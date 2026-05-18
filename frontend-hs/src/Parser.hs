{-# LANGUAGE OverloadedStrings #-}

module Parser (
  parseProgram,
) where

import Ast
import Control.Monad (void)
import qualified Data.Char as Char
import Data.Text (Text)
import qualified Data.Text as T
import qualified Data.Text.Read as TR
import Data.Void (Void)
import Numeric (readHex, readOct)
import Text.Megaparsec hiding (sepBy, sepEndBy)
import qualified Text.Megaparsec as Mp
import Text.Megaparsec.Char
import Text.Megaparsec.Pos (unPos)

type P = Parsec Void Text

parseProgram :: FilePath -> Text -> Either String Program
parseProgram fp src =
  case Mp.runParser (pProg fp <* eof) fp src of
    Left eb -> Left (errorBundlePretty eb)
    Right p -> Right p

------------------------------------------------------------------------------
-- trivia

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
  Span fp
    (fromIntegral . unPos $ Mp.sourceLine a)
    (fromIntegral . unPos $ Mp.sourceColumn a)
    (fromIntegral . unPos $ Mp.sourceLine b)
    (fromIntegral . unPos $ Mp.sourceColumn b)
    False

withSpan :: FilePath -> P x -> P (Span, x)
withSpan fp p = do
  pa <- Mp.getSourcePos
  x <- p
  pb <- Mp.getSourcePos
  pure (mkSpan fp pa pb, x)

kwBoundary :: P ()
kwBoundary = void . notFollowedBy $ satisfy (\c -> Char.isAlphaNum c || c == '_')

keyword :: Text -> P ()
keyword k = hj *> chunk k *> kwBoundary

sym :: Text -> P ()
sym t = hj *> chunk t

symbolic :: Text -> P ()
symbolic t = hj *> chunk t *> hj

identLetter :: Char -> Bool
identLetter c = Char.isAlpha c || c == '_'

identCont :: Char -> Bool
identCont c = Char.isAlphaNum c || c == '_'

identTok :: P Text
identTok = do
  c <- satisfy identLetter <?> "identifier"
  cs <- Mp.many (satisfy identCont)
  let nm = T.pack (c : cs)
  if nm == "similar" then fail "similar reserved" else if nm == "_" then fail "underscore reserved" else pure nm

------------------------------------------------------------------------------
-- escapes

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
    | otherwise =
        let ch = inner !! i
         in if ch /= '\\'
              then go (i + 1) (ch : acc)
              else
                if i + 1 >= n
                  then go (i + 1) ('\\' : acc)
                  else
                    let e = inner !! (i + 1)
                     in case simpleEsc e of
                          Just z -> go (i + 2) (z : acc)
                          Nothing
                            | e >= '0' && e <= '7' ->
                                let end = octEnd (i + 1) 1
                                    numStr = slice (i + 1) end
                                 in case readOct numStr of
                                      [(val, [])] -> go end (Char.chr val : acc)
                                      _ -> go (i + 2) (e : '\\' : acc)
                            | e == 'x' || e == 'u' || e == 'U' ->
                                case hexWidth e of
                                  Nothing -> go (i + 2) (e : '\\' : acc)
                                  Just width ->
                                    let start = i + 2
                                        end = start + width
                                     in if end <= n && all (\j -> isHexDigit (inner !! j)) [start .. end - 1]
                                          then case readHex (slice start end) of
                                            [(v, [])]
                                              | v >= 0 && v <= Char.ord Char.maxBound ->
                                                  go end (Char.chr v : acc)
                                              | otherwise ->
                                                  go (i + 2) (e : '\\' : acc)
                                            _ ->
                                              go (i + 2) (e : '\\' : acc)
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

------------------------------------------------------------------------------
-- literals & budget decomposition (Python `_parse_unit_token`)

parseUnitToken :: Text -> (Text, BudgetNum, Text)
parseUnitToken raw =
  let s = T.strip raw
      rd :: Text -> Integer
      rd t = either (\_ -> error "bad int literal") fst (TR.decimal (T.strip t))
      usdAmt :: BudgetNum
      usdAmt = either (\_ -> BNFloat (read $ T.unpack $ T.tail s)) (BNFloat . realToFrac . fst) (TR.double $ T.tail s)
   in case T.words s of
        [nw, "tokens"] -> ("tokens", BNInt (rd nw), raw)
        [nw, "turns"] -> ("turns", BNInt (rd nw), raw)
        _ ->
          if "$" `T.isPrefixOf` s
            then ("usd", usdAmt, raw)
            else
              if "ms" `T.isSuffixOf` s
                then ("ms", BNInt $ rd $ T.dropEnd 2 s, raw)
                else
                  case T.stripSuffix "s" s of
                    Just base
                      | T.all Char.isDigit base -> ("s", BNInt (rd base), raw)
                    _ ->
                      ("", BNInt (rd s), raw)

-----------------------------------------------------------------------------
-- Program

pProg :: FilePath -> P Program
pProg fp =
  hj *> fills *>
    ( do
        body <- sepEndBy (topStmt fp) stmtSep
        hj *> fills *> eof
        pure (Program (Span fp 1 1 1 1 False) body)
    )

topStmt :: FilePath -> P Stmt
topStmt fp =
  choice
    [ try $ matchThrStmt fp,
      try $ decoratedTop fp,
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
-- Decorators & @match_threshold

decorator :: FilePath -> P Decorator
decorator fp = do
  (sp, nm, args) <-
    withSpan fp $ do
      _ <- sym "@"
      n <- identTok
      xs <- option [] ((symbolic "(" *> sepEndBy (arg fp) comma <* symbolic ")") <|> pure [])
      pure (n, xs)
  _ <- void (Mp.some eoline)
  pure (Decorator sp nm args)

decoratedTop :: FilePath -> P Stmt
decoratedTop fp = do
  ds <- Mp.some (decorator fp)
  tg <- decoratedTarget fp
  pure (attachDecorators ds tg)

decoratedTarget :: FilePath -> P Stmt
decoratedTarget fp =
  choice
    [ StmtFn <$> pFn fp,
      StmtAgent <$> pAgent fp,
      StmtPrompt <$> pPrompt fp,
      StmtClass <$> pClass fp
    ]

attachDecorators :: [Decorator] -> Stmt -> Stmt
attachDecorators ds = \case
  StmtFn f -> StmtFn f {fnDecorators = ds <> fnDecorators f}
  StmtAgent a -> StmtAgent a {agDecorators = ds <> agDecorators a}
  StmtPrompt p -> StmtPrompt p {prDecorators = ds <> prDecorators p}
  StmtClass c -> StmtClass c {clDecorators = ds <> clDecorators c}
  x -> x

matchThrStmt :: FilePath -> P Stmt
matchThrStmt fp = do
  _ <- sym "@" *> keyword "match_threshold" *> symbolic "("
  thr <- numberLiteral fp
  _ <- symbolic ")"
  stmtSep
  StmtMatch m <- stmt fp >>= \sx -> case sx of StmtMatch sm -> pure (StmtMatch sm); _ -> fail "expected match"
  d <- exprToDouble thr
  pure $ StmtMatch m {msThreshold = Just d}

exprToDouble :: Expr -> P Double
exprToDouble = \case
  ExprFloatLit _ d -> pure d
  ExprIntLit _ i -> pure (fromIntegral i)
  _ -> fail "number literal expected"

