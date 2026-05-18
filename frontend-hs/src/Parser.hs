{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE TupleSections #-}

module Parser (parseProgram) where

import Ast
import Control.Applicative (optional, (<|>))
import Control.Monad (void)
import Data.List (foldl')
import Data.Maybe (fromMaybe)
import qualified Data.Char as Char
import qualified Data.Map.Strict as Map
import Data.Text (Text)
import qualified Data.Text as T
import qualified Data.Text.Read as TR
import Data.Void (Void)
import Numeric (readHex, readOct)
import Text.Megaparsec
import qualified Text.Megaparsec as Mp
import Text.Megaparsec.Char
import Text.Megaparsec.Pos (unPos)

type P = Parsec Void Text

parseProgram :: FilePath -> Text -> Either String Program
parseProgram fp txt =
  case Mp.runParser (pProg fp <* eof) fp txt of
    Left eb -> Left (errorBundlePretty eb)
    Right p -> Right p

------------------------------------------------------------------------------
hj :: P ()
hj =
  void . Mp.many $
    choice
      [ void (Mp.takeWhile1P Nothing (\c -> c == ' ' || c == '\t')),
        try $ char '#' >> void (Mp.takeWhileP Nothing (/= '\n'))
      ]

fills :: P ()
fills = void . Mp.many $ choice [try eoline, hj]

eoline :: P ()
eoline = void . try $ optionally (chunk "\r") *> chunk "\n"

stmtSep :: P ()
stmtSep = hj *> fills *> void (Mp.some eoline) *> hj *> fills

------------------------------------------------------------------------------
mkSpan :: FilePath -> Mp.SourcePos -> Mp.SourcePos -> Span
mkSpan fp a b =
  Span fp (ni $ Mp.sourceLine a) (ni $ Mp.sourceColumn a) (ni $ Mp.sourceLine b) (ni $ Mp.sourceColumn b) False
 where
  ni = fromIntegral . unPos

withSpan :: FilePath -> P x -> P (Span, x)
withSpan fp p = do
  pa <- Mp.getSourcePos
  x <- p
  pb <- Mp.getSourcePos
  pure (mkSpan fp pa pb, x)

------------------------------------------------------------------------------
kwBoundary :: P ()
kwBoundary = void . notFollowedBy $ satisfy (\c -> Char.isAlphaNum c || c == '_')

keyword :: Text -> P ()
keyword k = hj *> chunk k *> kwBoundary

sym :: Text -> P ()
sym t = hj *> chunk t

symbolic :: Text -> P ()
symbolic t = hj *> chunk t *> hj

commaTok :: P ()
commaTok = symbolic ","

identLetter :: Char -> Bool
identLetter c = Char.isAlpha c || c == '_'

identCont :: Char -> Bool
identCont c = Char.isAlphaNum c || c == '_'

identTok :: P Text
identTok = do
  hj
  c <- satisfy identLetter <?> "identifier"
  cs <- Mp.many (satisfy identCont)
  let nm = T.pack (c : cs)
  if nm == "similar" || nm == "_" then fail "identifier" else pure nm

------------------------------------------------------------------------------
simpleEsc :: Char -> Maybe Char
simpleEsc =
  flip lookup [('\"', '\"'), ('\'', '\''), ('\\', '\\'), ('a', '\a'), ('b', '\b'), ('f', '\f'), ('n', '\n'), ('r', '\r'), ('t', '\t'), ('v', '\v')]

isHexDigit :: Char -> Bool
isHexDigit c =
  Char.isDigit c || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')

decodeEscaped :: String -> String
decodeEscaped inner = go 0 ""
 where
  n = length inner
  go i acc
    | i >= n = reverse acc
    | inner !! i /= '\\' = go (i + 1) (inner !! i : acc)
    | i + 1 >= n = go (i + 1) ('\\' : acc)
    | otherwise =
        let e = inner !! (i + 1)
         in case simpleEsc e of
              Just z -> go (i + 2) (z : acc)
              Nothing
                | e >= '0' && e <= '7' ->
                    let end = octEnd (i + 1) 1
                        ns = slice (i + 1) end
                     in case readOct ns of
                          [(val, [])] -> go end (Char.chr val : acc)
                          _ -> go (i + 2) (e : '\\' : acc)
                | e == 'x' || e == 'u' || e == 'U' ->
                    case hexWidth e of
                      Nothing -> go (i + 2) (e : '\\' : acc)
                      Just width ->
                        let start = i + 2
                            endEx = start + width
                         in if endEx <= n && all (\j -> isHexDigit (inner !! j)) [start .. endEx - 1]
                              then case readHex (slice start endEx) of
                                [(v, [])]
                                  | v >= 0 && v <= Char.ord Char.maxBound ->
                                      go endEx (Char.chr v : acc)
                                  | otherwise -> go (i + 2) (e : '\\' : acc)
                                _ -> go (i + 2) (e : '\\' : acc)
                              else go (i + 2) (e : '\\' : acc)
                | otherwise -> go (i + 2) (e : '\\' : acc)
 where
  slice lo hi = take (hi - lo) (drop lo inner)
  octEnd j cnt
    | cnt >= 3 || j >= n = j
    | inner !! j >= '0' && inner !! j <= '7' = octEnd (j + 1) (cnt + 1)
    | otherwise = j

hexWidth :: Char -> Maybe Int
hexWidth = flip lookup [('x', 2), ('u', 4), ('U', 8)]

parseUnitToken :: Text -> (Text, BudgetNum, Text)
parseUnitToken raw =
  let s = T.strip raw
      rd t = either (\_ -> error "int") fst (TR.decimal (T.strip t))
      usdAmt =
        either (\_ -> BNFloat (read $ T.unpack $ T.tail s)) (BNFloat . realToFrac . fst) (TR.double $ T.tail s)
   in case T.words s of
        [nw, "tokens"] -> ("tokens", BNInt (rd nw), raw)
        [nw, "turns"] -> ("turns", BNInt (rd nw), raw)
        _
          | "$" `T.isPrefixOf` s -> ("usd", usdAmt, raw)
          | "ms" `T.isSuffixOf` s -> ("ms", BNInt $ rd $ T.dropEnd 2 s, raw)
          | otherwise ->
              case T.stripSuffix "s" s of
                Just base
                  | T.all Char.isDigit base -> ("s", BNInt (rd base), raw)
                _ -> ("", BNInt (rd s), raw)

------------------------------------------------------------------------------
pProg :: FilePath -> P Program
pProg fp =
  hj *> fills *> (Program (Span fp 1 1 1 1 False) <$> sepEndBy (topStmt fp) stmtSep) <* hj <* eof

topStmt :: FilePath -> P Stmt
topStmt fp =
  choice
    [ try (matchThrStmt fp),
      try (decoratedTop fp),
      try declNaked,
      stmt fp
    ]
 where
  declNaked =
    choice
      [ StmtFn <$> pFn fp,
        StmtAgent <$> pAgent fp,
        StmtPrompt <$> pPrompt fp,
        StmtClass <$> pClass fp,
        StmtUse <$> pUse fp
      ]

-----------------------------------------------------------------------------
decorator :: FilePath -> P Decorator
decorator fp = do
  (sp, nm, ax) <-
    withSpan fp $
      (\n a -> (n, a)) <$> (sym "@" *> identTok) <*> optArgs
  void (Mp.some eoline)
  pure (Decorator sp nm ax)
 where
  optArgs =
    maybe [] id <$> optional (try (symbolic "(" *> sepEndBy (arg fp) commaTok <* symbolic ")"))

decoratedTop :: FilePath -> P Stmt
decoratedTop fp = do
  ds <- Mp.some (decorator fp)
  tg <- decoratedTarget fp
  pure (wrapDecs ds tg)

wrapDecs :: [Decorator] -> Stmt -> Stmt
wrapDecs ds = \case
  StmtFn f -> StmtFn f {fnDecorators = ds}
  StmtAgent a -> StmtAgent a {agDecorators = ds}
  StmtPrompt p -> StmtPrompt p {prDecorators = ds}
  StmtClass c -> StmtClass c {clDecorators = ds}
  s -> s

decoratedTarget :: FilePath -> P Stmt
decoratedTarget fp =
  choice [StmtFn <$> pFn fp, StmtAgent <$> pAgent fp, StmtPrompt <$> pPrompt fp, StmtClass <$> pClass fp]

matchThrStmt :: FilePath -> P Stmt
matchThrStmt fp = do
  _ <- sym "@" *> keyword "match_threshold" *> symbolic "("
  thr <- gateNumberLit fp
  _ <- symbolic ")"
  fills *> Mp.some eoline *> fills
  StmtMatch <$> (matchAst fp (Just <$> litToDouble thr))

litToDouble :: Expr -> P Double
litToDouble = \case
  ExprFloatLit _ d -> pure d
  ExprIntLit _ i -> pure (fromIntegral i)
  _ -> fail "number literal expected"

------------------------------------------------------------------------------
glueSpan :: Span -> Span -> Span
glueSpan a b =
  Span (spanFile a) (spanLineStart a) (spanColStart a) (spanLineEnd b) (spanColEnd b) (spanSynthetic a || spanSynthetic b)

block :: FilePath -> P [Stmt]
block fp =
  symbolic "{" *> fills *> sepEndBy (stmt fp) stmtSep <* fills <* symbolic "}"

stmt :: FilePath -> P Stmt
stmt fp =
  choice
    [ try (matchThrStmt fp),
      try (letStmt fp),
      try (ifStmt fp),
      try (matchStmt fp),
      try (ctxStmt fp),
      try (withinStmt fp),
      try (tryStmt fp),
      try (retStmt fp),
      try (yieldStmt fp),
      try (includeStmt fp),
      StmtExpr <$> exprStmt fp
    ]

exprStmt :: FilePath -> P StmtExpr_
exprStmt fp = uncurry StmtExpr_ <$> withSpan fp (expr fp)

letStmt :: FilePath -> P Stmt
letStmt fp =
  (\(sp, (nm, tp, vx)) -> StmtLet LetStmt_{lsSpan = sp, lsName = nm, lsTypeAnnot = tp, lsValue = vx})
    <$> withSpan fp inner
 where
  inner =
    (,,)
      <$> (keyword "let" *> identTok)
      <*> optional (sym ":" *> typeExpr fp)
      <*> optional (sym "=" *> expr fp)

ifStmt :: FilePath -> P Stmt
ifStmt fp = StmtIf <$> ((\(sp, (c, th, el)) -> IfStmt_ sp c th el) <$> withSpan fp inner)
 where
  inner =
    (,,)
      <$> (keyword "if" *> ifCondition fp)
      <*> (symbolic "{" *> block fp <* symbolic "}")
      <*> optional (keyword "else" *> symbolic "{" *> block fp <* symbolic "}")

ifCondition :: FilePath -> P IfCondition
ifCondition fp =
  choice
    [ try (IfCondGate <$> confidenceGate fp),
      IfCondExpr <$> expr fp
    ]

confidenceGate :: FilePath -> P ConfidenceGate_
confidenceGate fp = (\(sp, (targ, op, d)) -> ConfidenceGate_ sp targ op d) <$> withSpan fp cg
 where
  cg =
    (,,)
      <$> expr fp
      <*> (sym "@" *> keyword "p" *> cmpTok)
      <*> (litToDouble =<< gateNumberLit fp)

cmpTok :: P Text
cmpTok =
  hj
    *> choice
      [ try $ chunk "<=" *> pure "<=",
        try $ chunk ">=" *> pure ">=",
        try $ chunk "==" *> pure "==",
        try $ chunk "!=" *> pure "!=",
        try $ chunk "<" *> pure "<",
        chunk ">" *> pure ">"
      ]

matchStmt :: FilePath -> P Stmt
matchStmt fp = StmtMatch <$> matchAst fp Nothing

matchAst :: FilePath -> Maybe Double -> P MatchStmt_
matchAst fp mbTh =
  (\(sp, (scr, cs)) -> MatchStmt_ sp scr cs mbTh)
    <$> withSpan fp inner
 where
  inner =
    (,)
      <$> (keyword "match" *> expr fp)
      <*>
        ( symbolic "{"
            *> hj
            *> fills
            *> Mp.sepBy1 (matchCase fp) (fills *> Mp.some eoline *> hj *> fills)
            <* fills
            <* symbolic "}"
        )

matchCase :: FilePath -> P MatchCase_
matchCase fp = (\(sp, (pat, bd)) -> MatchCase_ sp pat bd) <$> withSpan fp inner
 where
  inner =
    (,)
      <$> (keyword "case" *> pattern fp <* symbolic "=>")
      <*> matchCaseBody fp

matchCaseBody :: FilePath -> P [Stmt]
matchCaseBody fp =
  choice
    [ block fp,
      (\e ->
         let sp = exprSpan e
          in [StmtExpr StmtExpr_{sxSpan = sp, sxExpr = e}])
        <$> expr fp
    ]

pattern :: FilePath -> P Pattern
pattern fp =
  choice
    [ try $ (\(sp, t) -> PatSimilar SimilarPat_{ssSpan = sp, ssText = t}) <$> withSpan fp (keyword "similar" *> symbolic "(" *> doubleStringChunks <* symbolic ")"),
      try $ (\(sp, ()) -> PatWildcard sp) <$> withSpan fp (underscoreTok *> pure ()),
      PatExpr . uncurry ExprPat_ <$> withSpan fp (expr fp)
    ]

underscoreTok :: P ()
underscoreTok = sym "_" *> notFollowedBy (satisfy identCont)

ctxStmt :: FilePath -> P Stmt
ctxStmt fp = StmtCtx <$> ((\(sp, (b, sts)) -> CtxStmt_ sp b sts) <$> withSpan fp inner)
 where
  inner =
    (,)
      <$> (keyword "ctx" *> symbolic "(" *> budgetKwarg fp <* symbolic ")")
      <*> (symbolic "{" *> block fp <* symbolic "}")

withinStmt :: FilePath -> P Stmt
withinStmt fp = StmtWithin <$> ((\(sp, (bs, prim, fb)) -> WithinStmt_ sp bs prim fb) <$> withSpan fp inner)
 where
  inner =
    (,,)
      <$> ( keyword "within"
              *> keyword "budget"
              *> symbolic "("
              *> sepEndBy (budgetKwarg fp) commaTok
              <* symbolic ")"
          )
      <*> (symbolic "{" *> block fp <* symbolic "}")
      <*> optional (keyword "fallback" *> symbolic "{" *> block fp <* symbolic "}")

budgetKwarg :: FilePath -> P BudgetArg
budgetKwarg fp = do
  (spNm, nm) <- withSpan fp identTok
  _ <- symbolic ":"
  val <- budgetKwArgValue fp
  pure $ mergeBudgetKw spNm nm val

budgetKwArgValue :: FilePath -> P BudgetValue
budgetKwArgValue fp =
  choice
    [ BVParsed <$> try (budgetLiteral fp),
      BVBare <$> gateNumberLit fp
    ]

data BudgetValue
  = BVParsed !BudgetArg
  | BVBare !Expr

mergeBudgetKw :: Span -> Text -> BudgetValue -> BudgetArg
mergeBudgetKw spanNm nm = \case
  BVParsed b -> b {budgetSpan = glueSpan spanNm (budgetSpan b), budgetKwName = nm}
  BVBare e ->
    let v = case e of ExprIntLit _ i -> BNInt i; ExprFloatLit _ d -> BNFloat d; _ -> BNInt 0
        txt = case e of ExprIntLit _ i -> T.pack $ show i; ExprFloatLit _ d -> T.pack $ show d; _ -> ""
     in BudgetArg (glueSpan spanNm (exprSpan e)) nm nm v txt

tryStmt :: FilePath -> P Stmt
tryStmt fp = StmtTry <$> ((\(sp, (tb, exc, cb)) -> TryStmt_ sp tb exc cb) <$> withSpan fp inner)
 where
  inner =
    (,,)
      <$> (keyword "try" *> symbolic "{" *> block fp <* symbolic "}")
      <*> (keyword "catch" *> optional identTok)
      <*> (symbolic "{" *> block fp <* symbolic "}")

retStmt :: FilePath -> P Stmt
retStmt fp = StmtReturn <$> ((\(sp, v) -> ReturnStmt_ sp v) <$> withSpan fp inner)
 where
  inner = (,) <$> (keyword "return" *> optional (try (expr fp)))

yieldStmt :: FilePath -> P Stmt
yieldStmt fp = StmtYield <$> ((\(sp, v) -> YieldStmt_ sp v) <$> withSpan fp inner)
 where
  inner = (,) <$> (keyword "yield" *> optional (try (expr fp)))

includeStmt :: FilePath -> P Stmt
includeStmt fp = StmtInclude <$> ((\(sp, e) -> IncludeStmt_ sp e) <$> withSpan fp (keyword "include" *> expr fp))

------------------------------------------------------------------------------
tabsOnly :: P ()
tabsOnly = void $ Mp.takeWhile1P Nothing (\c -> c == ' ' || c == '\t')

expr :: FilePath -> P Expr
expr fp = lambdaExpr fp <|> spawnExpr fp <|> orExpr fp

lambdaExpr :: FilePath -> P Expr
lambdaExpr fp =
  choice
    [ lamSingle,
      lamMulti
    ]
 where
  lamSingle =
    (\(sp, (n, b)) -> ExprLambda (Lambda_ sp [Param sp n Nothing Nothing] b))
      <$> try (withSpan fp ((,) <$> identTok <* symbolic "=>" <*> expr fp))
  lamMulti =
    (\(sp, (ps, b)) -> ExprLambda (Lambda_ sp ps b))
      <$> withSpan fp
        ( (,) <$> (symbolic "(" *> sepEndBy (lambdaParam fp) commaTok <* symbolic ")")
            <*> (symbolic "=>" *> expr fp)
        )

lambdaParam :: FilePath -> P Param
lambdaParam fpP = do
  (spm, nm) <- withSpan fpP identTok
  ta <- optional (sym ":" *> typeExpr fpP)
  pure $ Param spm nm ta Nothing

spawnExpr :: FilePath -> P Expr
spawnExpr fp = do
  (sp, t) <- withSpan fp (keyword "spawn" *> postfix fp)
  normalizeSpawn sp t

normalizeSpawn :: Span -> Expr -> P Expr
normalizeSpawn sp e = case e of
  ExprCall c -> pure $ ExprSpawn (Spawn_ sp c)
  ExprIdent sid nm ->
    pure $
      ExprSpawn
        ( Spawn_
            sp
            Call_
              { cllSpan = glueSpan sid sid,
                callee = ExprIdent sid nm,
                callArgs = []
              }
        )
  _ ->
    fail "spawn expects a parenthesized call or bare identifier"

------------------------------------------------------------------------------
orExpr :: FilePath -> P Expr
orExpr fp = chainBin "or" (andExpr fp)

andExpr :: FilePath -> P Expr
andExpr fp = chainBin "and" (notExpr fp)

notExpr :: FilePath -> P Expr
notExpr fp =
  choice
    [ (\(sp, e) -> ExprUnaryOp (UnaryOp_ sp "not" e)) <$> try (withSpan fp (keyword "not" *> notExpr fp)),
      cmpExpr fp
    ]

chainBin :: Text -> P Expr -> P Expr
chainBin op inner = do
  a <- inner
  rs <- Mp.many (try (keyword op *> inner))
  pure (foldl' (glueBin op) a rs)

glueBin :: Text -> Expr -> Expr -> Expr
glueBin op l r =
  ExprBinOp (BinOp_ (glueSpan (exprSpan l) (exprSpan r)) op l r)

cmpExpr :: FilePath -> P Expr
cmpExpr fp = do
  x <- addExpr fp
  rs <- Mp.many (try ((,) <$> cmpTok <*> addExpr fp))
  pure $ foldl' (\acc (cop, rhs) -> ExprBinOp (BinOp_ (glueSpan (exprSpan acc) (exprSpan rhs)) cop acc rhs)) x rs

addExpr :: FilePath -> P Expr
addExpr fp = chainPM ["+", "-"] (mulExpr fp)

mulExpr :: FilePath -> P Expr
mulExpr fp = chainPM ["*", "/"] (unary fp)

chainPM :: [Text] -> P Expr -> P Expr
chainPM ops base = do
  x <- base
  rest <- Mp.many (choice (map tryOp ops))
  pure $ foldl' (\acc (op, rhs) -> ExprBinOp (BinOp_ (glueSpan (exprSpan acc) (exprSpan rhs)) op acc rhs)) x rest
 where
  tryOp op = try ((,) <$> symbolic op <*> base)

unary :: FilePath -> P Expr
unary fp =
  choice
    [ (\(sp, u) -> ExprUnaryOp (UnaryOp_ sp "-" u))
        <$> try (withSpan fp (symbolic "-" *> unary fp)),
      postfix fp
    ]

postfix :: FilePath -> P Expr
postfix fp = do
  hd <- primary fp
  fs <- Mp.many (suffixStep fp)
  pure (foldl' (\acc f -> f acc) hd fs)

suffixStep :: FilePath -> P (Expr -> Expr)
suffixStep fp =
  choice
    [ callSuffix fp,
      memberSuffix fp,
      indexSuffix fp
    ]

callSuffix :: FilePath -> P (Expr -> Expr)
callSuffix fp = do
  args <- symbolic "(" *> sepEndBy (arg fp) commaTok <* symbolic ")"
  pure $ \e ->
    ExprCall
      Call_
        { cllSpan = glueCall e args,
          callee = e,
          callArgs = args
        }

memberSuffix :: FilePath -> P (Expr -> Expr)
memberSuffix fp = do
  (sp_nm, nm) <- symbolic "." *> withSpan fp identTok
  pure $ \obj ->
    ExprMember
      Member_
        { mbSpan = glueSpan (exprSpan obj) sp_nm,
          mbObj = obj,
          mbAttr = nm
        }

indexSuffix :: FilePath -> P (Expr -> Expr)
indexSuffix fp = do
  ix <- symbolic "[" *> expr fp <* symbolic "]"
  pure $ \obj ->
    ExprIndex
      Index_
        { ixSpan = glueSpan (exprSpan obj) (exprSpan ix),
          ixObj = obj,
          ixIndex = ix
        }

glueCall :: Expr -> [Arg] -> Span
glueCall e as =
  case as of
    [] -> exprSpan e
    xs -> glueSpan (exprSpan e) (argSpan $ last xs)

------------------------------------------------------------------------------
primary :: FilePath -> P Expr
primary fp =
  choice
    [ try $ ExprBudget <$> budgetLiteral fp,
      try $ litExpr fp,
      symbolic "(" *> expr fp <* symbolic ")",
      (\(sp, xs) -> ExprList $ ListLit_ sp xs)
        <$> withSpan fp (symbolic "[" *> sepEndBy (expr fp) commaTok <* symbolic "]"),
      ExprDict <$> dictLit fp,
      (\(sp, nm) -> ExprIdent sp nm) <$> withSpan fp identTok
    ]

------------------------------------------------------------------------------
litExpr :: FilePath -> P Expr
litExpr fp =
  choice
    [ (\(sp, t) -> ExprStrLit sp t True) <$> withSpan fp tripleStringChunks,
      (\(sp, t) -> ExprStrLit sp t False) <$> withSpan fp doubleStringChunks,
      numberExpr fp,
      (\(sp, b) -> ExprBoolLit sp b) <$> withSpan fp boolLit,
      (\(sp, ()) -> ExprNullLit sp) <$> withSpan fp (keyword "null" *> pure ())

    ]

boolLit :: P Bool
boolLit =
  True <$ keyword "true"
    <|> False <$ keyword "false"

doubleStringChunks :: P Text
doubleStringChunks =
  hj *> char '"' *> (T.pack <$> Mp.many ch) <* char '"'
 where
  ch =
    choice
      [ '\"' <$ try (chunk "\\\""),
        '\\' <$ try (chunk "\\\\"),
        '\n' <$ try (chunk "\\n"),
        '\t' <$ try (chunk "\\t"),
        '\r' <$ try (chunk "\\r"),
        satisfy (\c -> c /= '"' && c /= '\\')
      ]

tripleStringChunks :: P Text
tripleStringChunks =
  hj
    *> chunk "\"\"\""
    *> (T.pack <$> Mp.manyTill Mp.anySingle (try $ chunk "\"\"\""))

gateNumberLit :: FilePath -> P Expr
gateNumberLit = numberExpr

numberExpr :: FilePath -> P Expr
numberExpr fp =
  (\(sp, v) -> either (ExprIntLit sp) (ExprFloatLit sp) v)
    <$> withSpan fp numberAtom

numberAtom :: P (Either Integer Double)
numberAtom = hj *> lexNumText

lexNumText :: P (Either Integer Double)
lexNumText = do
  whole <- Mp.takeWhile1P Nothing Char.isDigit
  mfrac <- optional $ try (chunk "." *> Mp.takeWhile1P Nothing Char.isDigit)
  case mfrac of
    Nothing ->
      case TR.decimal whole of
        Right (i, r) | T.null r -> pure (Left i)
        _ -> fail "invalid integer literal"
    Just frac ->
      let txt = whole <> "." <> frac
       in case TR.double txt of
            Right (d, r) | T.null r -> pure (Right d)
            _ -> fail "invalid float literal"

------------------------------------------------------------------------------
budgetLiteral :: FilePath -> P BudgetArg
budgetLiteral fp =
  (\(sp, rawTxt) ->
     let !(u, num, rr) = parseUnitToken rawTxt
      in BudgetArg sp "" u num rr)
    <$> withSpan fp budgetLexeme

budgetLexeme :: P Text
budgetLexeme =
  hj
    *> choice
    [ try usdLit,
      try tokensLit,
      try turnsLit,
      try msLit,
      sLit
    ]

tokensLit :: P Text
tokensLit = do
  w <- Mp.takeWhile1P Nothing Char.isDigit
  tabsOnly
  _ <- chunk "tokens"
  kwBoundary
  pure (w <> " tokens")

turnsLit :: P Text
turnsLit = do
  w <- Mp.takeWhile1P Nothing Char.isDigit
  tabsOnly
  _ <- chunk "turns"
  kwBoundary
  pure (w <> " turns")

msLit :: P Text
msLit = do
  w <- Mp.takeWhile1P Nothing Char.isDigit
  _ <- chunk "ms"
  kwBoundary
  pure (w <> "ms")

sLit :: P Text
sLit = do
  w <- Mp.takeWhile1P Nothing Char.isDigit
  _ <- chunk "s"
  kwBoundary
  pure (w <> "s")

usdLit :: P Text
usdLit = do
  _ <- chunk "$"
  whole <- Mp.takeWhile1P Nothing Char.isDigit
  frac <- optional (try (chunk "." *> Mp.takeWhile1P Nothing Char.isDigit))
  _ <- kwBoundary
  pure $ case frac of
    Nothing -> "$" <> whole
    Just f -> "$" <> whole <> "." <> f

------------------------------------------------------------------------------
dictLit :: FilePath -> P DictLit_
dictLit fp =
  (\(sp, items) -> DictLit_ sp items) <$> withSpan fp inner
 where
  inner =
    symbolic "{" *> sepEndBy (dictPair fp) commaTok <* symbolic "}"

dictPair :: FilePath -> P (Expr, Expr)
dictPair fp =
  (,)
    <$> dictKeyExpr fp
    <*> (symbolic ":" *> expr fp)

dictKeyExpr :: FilePath -> P Expr
dictKeyExpr fp =
  choice
    [ (\(sp, t) -> ExprStrLit sp t False) <$> withSpan fp doubleStringChunks,
      (\(sp, nm) -> ExprIdent sp nm) <$> withSpan fp identTok
    ]

------------------------------------------------------------------------------
arg :: FilePath -> P Arg
arg fp =
  choice
    [ try namedArg,
      posArg
    ]
 where
  namedArg = do
    (sn, nm) <- withSpan fp identTok
    _ <- symbolic ":"
    (sv, ex) <- withSpan fp (expr fp)
    pure Arg{argSpan = glueSpan sn sv, argName = Just nm, argValue = ex}
  posArg = do
    (sx, ex) <- withSpan fp (expr fp)
    pure Arg{argSpan = sx, argName = Nothing, argValue = ex}

------------------------------------------------------------------------------
qualName :: FilePath -> P QualName
qualName fp =
  (\(sp, segs) -> QualName sp segs)
    <$> withSpan fp segments
 where
  segments =
    (:)
      <$> identTok
      <*> many (sym "." *> identTok)

typeExpr :: FilePath -> P TypeExpr
typeExpr fp = do
  (sp, (qn, mg, mkw)) <- withSpan fp tyInner
  pure $ TypeExpr sp qn (fromMaybe [] mg) (fromMaybe [] mkw)
 where
  tyInner =
    (,,)
      <$> qualName fp
      <*> optional typeGenerics
      <*> optional typeKwargsBlk
  typeGenerics =
    try $
      symbolic "<"
        *> sepEndBy (typeExpr fp) commaTok
        <* symbolic ">"
  typeKwargsBlk =
    try $
      symbolic "("
        *> sepEndBy (typeKwarg fp) commaTok
        <* symbolic ")"

typeKwarg :: FilePath -> P TypeKwarg
typeKwarg fp = do
  (sn, nm) <- withSpan fp identTok
  _ <- symbolic ":"
  tv <- typeKwargValue fp
  pure $ TypeKwarg (glueSpan sn (typeKwargValSpan tv)) nm tv

typeKwargValSpan :: TypeKwargValue -> Span
typeKwargValSpan = \case
  TKVBudget b -> budgetSpan b
  TKVQual q -> qnSpan q
  TKVExpr e -> exprSpan e

typeKwargValue :: FilePath -> P TypeKwargValue
typeKwargValue fp =
  choice
    [ TKVBudget <$> try (budgetLiteral fp),
      TKVExpr <$> try (numberExpr fp),
      TKVExpr <$> try tripleStrKw,
      TKVExpr <$> try doubleStrKw,
      TKVExpr <$> try boolNullKw,
      TKVQual <$> qualName fp
    ]
 where
  tripleStrKw =
    (\(sp, t) -> ExprStrLit sp t True) <$> withSpan fp tripleStringChunks
  doubleStrKw =
    (\(sp, t) -> ExprStrLit sp t False) <$> withSpan fp doubleStringChunks
  boolNullKw =
    choice
      [ (\(sp, b) -> ExprBoolLit sp b) <$> withSpan fp boolLit,
        (\(sp, ()) -> ExprNullLit sp) <$> withSpan fp (keyword "null" *> pure ())
      ]

------------------------------------------------------------------------------
param :: FilePath -> P Param
param fp = do
  (sp, nm) <- withSpan fp identTok
  ta <- optional (sym ":" *> typeExpr fp)
  df <- optional (sym "=" *> expr fp)
  pure $ Param sp nm ta df

paramList :: FilePath -> P [Param]
paramList fp = sepEndBy (param fp) commaTok

------------------------------------------------------------------------------
pFn :: FilePath -> P FnDecl_
pFn fp =
  (\(sp, (nm, ps, rt, bd)) ->
     FnDecl_ sp nm ps rt bd [])
    <$> withSpan fp inner
 where
  inner =
    (,,,)
      <$> (keyword "fn" *> identTok)
      <*> (symbolic "(" *> paramList fp <* symbolic ")")
      <*> optional (sym "->" *> typeExpr fp)
      <*> (symbolic "{" *> block fp <* symbolic "}")

pAgent :: FilePath -> P AgentDecl_
pAgent fp =
  (\(sp, (nm, ps, rt, opts, bd)) ->
     AgentDecl_ sp nm ps rt opts bd [])
    <$> withSpan fp inner
 where
  inner =
    (,,,,)
      <$> (keyword "agent" *> identTok)
      <*> (symbolic "(" *> paramList fp <* symbolic ")")
      <*> optional (sym "->" *> typeExpr fp)
      <*> (symbolic "{" *> (agentInner fp <* symbolic "}"))

agentInner :: FilePath -> P (AgentOptions, [Stmt])
agentInner fp = do
  fills
  opts <- many (try (fills *> agentOpt fp <* stmtSep))
  fills
  sts <- sepEndBy (stmt fp) stmtSep
  fills
  pure (foldAgentOpts fp opts, sts)

agentOpt :: FilePath -> P (Text, Expr)
agentOpt fp =
  choice
    [ kv "system" (keyword "system"),
      kv "tools" (keyword "tools"),
      kv "model" (keyword "model"),
      kv "retries" (keyword "retries"),
      kv "memory" (keyword "memory")
    ]
 where
  kv lbl p =
    (\e -> (lbl, e)) <$> (p *> sym ":" *> expr fp)

foldAgentOpts :: FilePath -> [(Text, Expr)] -> AgentOptions
foldAgentOpts fp entries =
  AgentOptions (Span fp 1 1 1 1 False)
    (Map.lookup "system" m)
    (Map.lookup "tools" m)
    (Map.lookup "model" m)
    (Map.lookup "retries" m)
    (Map.lookup "memory" m)
 where
  m = Map.fromList entries

------------------------------------------------------------------------------
pPrompt :: FilePath -> P PromptDecl_
pPrompt fp =
  (\(sp, (nm, ext, bod)) ->
     PromptDecl_ sp nm ext bod [])
    <$> withSpan fp inner
 where
  inner =
    (,,)
      <$> (keyword "prompt" *> identTok)
      <*> optional (keyword "extends" *> qualName fp)
      <*> (symbolic "{" *> promptBody fp <* symbolic "}")

promptBody :: FilePath -> P [PromptStringLit]
promptBody fp =
  fills *> Mp.sepEndBy1 (promptLit fp) (fills *> Mp.some eoline *> fills) <* fills

promptLit :: FilePath -> P PromptStringLit
promptLit fp =
  choice
    [ (\(sp, t) -> PromptStringLit sp t True) <$> withSpan fp tripleStringChunks,
      (\(sp, t) -> PromptStringLit sp t False) <$> withSpan fp doubleStringChunks
    ]

------------------------------------------------------------------------------
pClass :: FilePath -> P ClassDecl_
pClass fp =
  (\(sp, (nm, flds)) ->
     ClassDecl_ sp nm flds [])
    <$> withSpan fp inner
 where
  inner =
    (,)
      <$> (keyword "class" *> identTok)
      <*> (symbolic "{" *> classBody fp <* symbolic "}")

classBody :: FilePath -> P [ClassField]
classBody fp =
  fills *> sepEndBy (classField fp) stmtSep <* fills

classField :: FilePath -> P ClassField
classField fp =
  (\(sp, (nm, ty, df)) ->
     ClassField sp nm ty df)
    <$> withSpan fp inner
 where
  inner =
    (,,)
      <$> identTok
      <*> (sym ":" *> typeExpr fp)
      <*> optional (sym "=" *> expr fp)

------------------------------------------------------------------------------
pUse :: FilePath -> P UseStmt_
pUse fp =
  (\(sp, (parts, als)) ->
     UseStmt_ sp parts als)
    <$> withSpan fp inner
 where
  inner =
    (,)
      <$> (keyword "use" *> usePathSegments)
      <*> optional (keyword "as" *> identTok)

usePathSegments :: P [Text]
usePathSegments =
  (:)
    <$> identTok
    <*> many (sym "::" *> identTok)
