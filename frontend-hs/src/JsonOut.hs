{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE TupleSections #-}

module JsonOut (
  encodeProgramPretty,
) where

import Ast
import qualified Data.Aeson as Aeson
import Data.Aeson ((.=))
import qualified Data.Aeson.Encode.Pretty as AP
import qualified Data.ByteString.Lazy as BL
import qualified Data.Text as T
import Data.Text (Text)
import qualified Data.Vector as Vec
import System.FilePath (takeFileName)

encodeProgramPretty :: Bool -> FilePath -> Program -> BL.ByteString
encodeProgramPretty normalize sourcePath =
  AP.encodePretty' conf (encodeProgram normalize sourcePath)
  where
    conf = AP.defConfig {AP.confIndent = AP.Spaces 2, AP.confCompare = AP.keyOrder []}

encodeProgram :: Bool -> FilePath -> Program -> Aeson.Value
encodeProgram normalize sourcePath prog =
  Aeson.object
    [ "_node" .= aesText "Program",
      "span" .= encodeSpan normalize sourcePath (programSpan prog),
      "body" .= map (encodeStmt normalize sourcePath) (body prog)
    ]

aesText :: Text -> Aeson.Value
aesText = Aeson.String

resolveFile :: FilePath -> Span -> FilePath
resolveFile fallback sp =
  if null (spanFile sp) then fallback else spanFile sp

encodeSpan :: Bool -> FilePath -> Span -> Aeson.Value
encodeSpan normalize sourcePath sp
  | spanSynthetic sp =
      Aeson.object
        [ "file" .= aesText (T.pack (spanFile sp)),
          "lines" .= ints [spanLineStart sp, spanLineEnd sp],
          "cols" .= ints [spanColStart sp, spanColEnd sp],
          "synthetic" .= True
        ]
  | normalize =
      let fp = resolveFile sourcePath sp
          fpShown = if fp == "<synthetic>" then fp else takeFileName fp
       in Aeson.object
            [ "file" .= aesText (T.pack fpShown),
              "lines" .= ints [0, 0],
              "cols" .= ints [0, 0],
              "synthetic" .= spanSynthetic sp
            ]
  | otherwise =
      let fp = spanFile sp
       in Aeson.object
            [ "file" .= aesText (T.pack fp),
              "lines" .= ints [spanLineStart sp, spanLineEnd sp],
              "cols" .= ints [spanColStart sp, spanColEnd sp],
              "synthetic" .= spanSynthetic sp
            ]
  where
    ints xs = Aeson.Array (Vec.fromList (map (Aeson.Number . fromIntegral) xs))

encodeStmt :: Bool -> FilePath -> Stmt -> Aeson.Value
encodeStmt normalize p = \case
  StmtExpr x -> encodeStmtExpr normalize p x
  StmtLet x -> encodeLet normalize p x
  StmtIf x -> encodeIf normalize p x
  StmtMatch x -> encodeMatch normalize p x
  StmtCtx x -> encodeCtx normalize p x
  StmtWithin x -> encodeWithin normalize p x
  StmtTry x -> encodeTry normalize p x
  StmtReturn x -> encodeReturn normalize p x
  StmtYield x -> encodeYield normalize p x
  StmtInclude x -> encodeInclude normalize p x
  StmtFn x -> encodeFn normalize p x
  StmtAgent x -> encodeAgent normalize p x
  StmtPrompt x -> encodePrompt normalize p x
  StmtClass x -> encodeClass normalize p x
  StmtUse x -> encodeUse normalize p x

encodeStmtExpr :: Bool -> FilePath -> StmtExpr_ -> Aeson.Value
encodeStmtExpr normalize p e =
  Aeson.object
    [ "_node" .= aesText "ExprStmt",
      "span" .= encodeSpan normalize p (sxSpan e),
      "expr" .= encodeExpr normalize p (sxExpr e)
    ]

encodeLet :: Bool -> FilePath -> LetStmt_ -> Aeson.Value
encodeLet normalize p e =
  Aeson.object
    [ "_node" .= aesText "LetStmt",
      "span" .= encodeSpan normalize p (lsSpan e),
      "name" .= aesText (lsName e),
      "type_annot" .= maybe Aeson.Null (encodeType normalize p) (lsTypeAnnot e),
      "value" .= maybe Aeson.Null (encodeExpr normalize p) (lsValue e)
    ]

encodeIf :: Bool -> FilePath -> IfStmt_ -> Aeson.Value
encodeIf normalize p e =
  Aeson.object
    [ "_node" .= aesText "IfStmt",
      "span" .= encodeSpan normalize p (ifsSpan e),
      "condition" .= encodeIfCond normalize p (ifsCondition e),
      "then_body" .= map (encodeStmt normalize p) (ifsThen e),
      "else_body"
        .= case ifsElse e of
          Nothing -> Aeson.Null
          Just sts -> Aeson.Array (Vec.fromList (map (encodeStmt normalize p) sts))
    ]

encodeIfCond :: Bool -> FilePath -> IfCondition -> Aeson.Value
encodeIfCond normalize p = \case
  IfCondExpr ex -> encodeExpr normalize p ex
  IfCondGate cg -> encodeConfGate normalize p cg

encodeConfGate :: Bool -> FilePath -> ConfidenceGate_ -> Aeson.Value
encodeConfGate normalize p g =
  Aeson.object
    [ "_node" .= aesText "ConfidenceGate",
      "span" .= encodeSpan normalize p (cgSpan g),
      "target" .= encodeExpr normalize p (cgTarget g),
      "op" .= aesText (cgOp g),
      "threshold" .= cgThreshold g
    ]

encodeMatch :: Bool -> FilePath -> MatchStmt_ -> Aeson.Value
encodeMatch normalize p m =
  Aeson.object
    [ "_node" .= aesText "MatchStmt",
      "span" .= encodeSpan normalize p (msSpan m),
      "scrutinee" .= encodeExpr normalize p (msScrutinee m),
      "cases" .= map (encodeMatchCase normalize p) (msCases m),
      "threshold" .= case msThreshold m of Nothing -> Aeson.Null; Just t -> Aeson.Number (realToFrac t)
    ]

encodeMatchCase :: Bool -> FilePath -> MatchCase_ -> Aeson.Value
encodeMatchCase normalize p c =
  Aeson.object
    [ "_node" .= aesText "MatchCase",
      "span" .= encodeSpan normalize p (mcSpan c),
      "pattern" .= encodePattern normalize p (mcPattern c),
      "body" .= map (encodeStmt normalize p) (mcBody c)
    ]

encodePattern :: Bool -> FilePath -> Pattern -> Aeson.Value
encodePattern normalize p = \case
  PatSimilar s ->
    Aeson.object
      [ "_node" .= aesText "SimilarPattern",
        "span" .= encodeSpan normalize p (ssSpan s),
        "text" .= aesText (ssText s)
      ]
  PatWildcard spanW ->
    Aeson.object
      [ "_node" .= aesText "WildcardPattern",
        "span" .= encodeSpan normalize p spanW
      ]
  PatExpr ep ->
    Aeson.object
      [ "_node" .= aesText "ExprPattern",
        "span" .= encodeSpan normalize p (epsSpan ep),
        "expr" .= encodeExpr normalize p (epsExpr ep)
      ]

encodeCtx :: Bool -> FilePath -> CtxStmt_ -> Aeson.Value
encodeCtx normalize p c =
  Aeson.object
    [ "_node" .= aesText "CtxBlock",
      "span" .= encodeSpan normalize p (cxSpan c),
      "budget" .= encodeBudgetArg normalize p (cxBudget c),
      "body" .= map (encodeStmt normalize p) (cxBody c)
    ]

encodeWithin :: Bool -> FilePath -> WithinStmt_ -> Aeson.Value
encodeWithin normalize p w =
  Aeson.object
    [ "_node" .= aesText "WithinFallback",
      "span" .= encodeSpan normalize p (wfSpan w),
      "budget_args" .= map (encodeBudgetArg normalize p) (wfBudgetArgs w),
      "primary" .= map (encodeStmt normalize p) (wfPrimary w),
      "fallback" .= case wfFallback w of
        Nothing -> Aeson.Null
        Just sts -> Aeson.Array (Vec.fromList (map (encodeStmt normalize p) sts))
    ]

encodeTry :: Bool -> FilePath -> TryStmt_ -> Aeson.Value
encodeTry normalize p t =
  Aeson.object
    [ "_node" .= aesText "TryCatch",
      "span" .= encodeSpan normalize p (tcSpan t),
      "try_body" .= map (encodeStmt normalize p) (tcTryBody t),
      "exc_name"
        .= case tcExcName t of Nothing -> Aeson.Null; Just n -> aesText n,
      "catch_body" .= map (encodeStmt normalize p) (tcCatchBody t)
    ]

encodeReturn :: Bool -> FilePath -> ReturnStmt_ -> Aeson.Value
encodeReturn normalize p r =
  Aeson.object
    [ "_node" .= aesText "ReturnStmt",
      "span" .= encodeSpan normalize p (rsSpan r),
      "value" .= maybe Aeson.Null (encodeExpr normalize p) (rsValue r)
    ]

encodeYield :: Bool -> FilePath -> YieldStmt_ -> Aeson.Value
encodeYield normalize p y =
  Aeson.object
    [ "_node" .= aesText "YieldStmt",
      "span" .= encodeSpan normalize p (ysSpan y),
      "value" .= maybe Aeson.Null (encodeExpr normalize p) (ysValue y)
    ]

encodeInclude :: Bool -> FilePath -> IncludeStmt_ -> Aeson.Value
encodeInclude normalize p i =
  Aeson.object
    [ "_node" .= aesText "IncludeStmt",
      "span" .= encodeSpan normalize p (isSpan i),
      "value" .= encodeExpr normalize p (isValue i)
    ]

encodeDecorator :: Bool -> FilePath -> Decorator -> Aeson.Value
encodeDecorator normalize p d =
  Aeson.object
    [ "_node" .= aesText "Decorator",
      "span" .= encodeSpan normalize p (decSpan d),
      "name" .= aesText (decName d),
      "args" .= map (encodeArg normalize p) (decArgs d)
    ]

encodeFn :: Bool -> FilePath -> FnDecl_ -> Aeson.Value
encodeFn normalize p f =
  Aeson.object
    [ "_node" .= aesText "FnDecl",
      "span" .= encodeSpan normalize p (fnSpan f),
      "name" .= aesText (fnName f),
      "params" .= map (encodeParam normalize p) (fnParams f),
      "return_type" .= maybe Aeson.Null (encodeType normalize p) (fnReturn f),
      "body" .= map (encodeStmt normalize p) (fnBody f),
      "decorators" .= map (encodeDecorator normalize p) (fnDecorators f)
    ]

encodeAgentOptions :: Bool -> FilePath -> AgentOptions -> Aeson.Value
encodeAgentOptions normalize p o =
  Aeson.object
    [ "_node" .= aesText "AgentOptions",
      "span" .= encodeSpan normalize p (aoSpan o),
      "system" .= maybe Aeson.Null (encodeExpr normalize p) (aoSystem o),
      "tools" .= maybe Aeson.Null (encodeExpr normalize p) (aoTools o),
      "model" .= maybe Aeson.Null (encodeExpr normalize p) (aoModel o),
      "retries" .= maybe Aeson.Null (encodeExpr normalize p) (aoRetries o),
      "memory" .= maybe Aeson.Null (encodeExpr normalize p) (aoMemory o)
    ]

encodeAgent :: Bool -> FilePath -> AgentDecl_ -> Aeson.Value
encodeAgent normalize p a =
  Aeson.object
    [ "_node" .= aesText "AgentDecl",
      "span" .= encodeSpan normalize p (agSpan a),
      "name" .= aesText (agName a),
      "params" .= map (encodeParam normalize p) (agParams a),
      "return_type" .= maybe Aeson.Null (encodeType normalize p) (agReturn a),
      "options" .= encodeAgentOptions normalize p (agOptions a),
      "body" .= map (encodeStmt normalize p) (agBody a),
      "decorators" .= map (encodeDecorator normalize p) (agDecorators a)
    ]

encodePromptString :: Bool -> FilePath -> PromptStringLit -> Aeson.Value
encodePromptString normalize p s =
  Aeson.object
    [ "_node" .= aesText "StringLit",
      "span" .= encodeSpan normalize p (pslSpan s),
      "value" .= aesText (pslValue s),
      "triple" .= pslTriple s
    ]

encodePrompt :: Bool -> FilePath -> PromptDecl_ -> Aeson.Value
encodePrompt normalize p pr =
  Aeson.object
    [ "_node" .= aesText "PromptDecl",
      "span" .= encodeSpan normalize p (prSpan pr),
      "name" .= aesText (prName pr),
      "extends" .= maybe Aeson.Null (encodeQual normalize p) (prExtends pr),
      "body" .= map (encodePromptString normalize p) (prBody pr),
      "decorators" .= map (encodeDecorator normalize p) (prDecorators pr)
    ]

encodeClass :: Bool -> FilePath -> ClassDecl_ -> Aeson.Value
encodeClass normalize p c =
  Aeson.object
    [ "_node" .= aesText "ClassDecl",
      "span" .= encodeSpan normalize p (clSpan c),
      "name" .= aesText (clName c),
      "fields" .= map (encodeClassField normalize p) (clFields c),
      "decorators" .= map (encodeDecorator normalize p) (clDecorators c)
    ]

encodeClassField :: Bool -> FilePath -> ClassField -> Aeson.Value
encodeClassField normalize p f =
  Aeson.object
    [ "_node" .= aesText "ClassField",
      "span" .= encodeSpan normalize p (cfSpan f),
      "name" .= aesText (cfName f),
      "type_annot" .= encodeType normalize p (cfType f),
      "default" .= maybe Aeson.Null (encodeExpr normalize p) (cfDefault f)
    ]

encodeUse :: Bool -> FilePath -> UseStmt_ -> Aeson.Value
encodeUse normalize p u =
  Aeson.object
    [ "_node" .= aesText "UseStmt",
      "span" .= encodeSpan normalize p (usSpan u),
      "path" .= map aesText (usPath u),
      "alias" .= case usAlias u of Nothing -> Aeson.Null; Just a -> aesText a
    ]

encodeQual :: Bool -> FilePath -> QualName -> Aeson.Value
encodeQual normalize p q =
  Aeson.object
    [ "_node" .= aesText "QualName",
      "span" .= encodeSpan normalize p (qnSpan q),
      "parts" .= map aesText (qnParts q)
    ]

encodeBudgetNum :: BudgetNum -> Aeson.Value
encodeBudgetNum = \case
  BNInt i -> Aeson.Number (fromIntegral i)
  BNFloat d -> Aeson.Number (realToFrac d)

encodeBudgetArg :: Bool -> FilePath -> BudgetArg -> Aeson.Value
encodeBudgetArg normalize p b =
  Aeson.object
    [ "_node" .= aesText "BudgetArg",
      "span" .= encodeSpan normalize p (budgetSpan b),
      "name" .= aesText (budgetKwName b),
      "unit" .= aesText (budgetUnit b),
      "value" .= encodeBudgetNum (budgetValue b),
      "raw" .= aesText (budgetRaw b)
    ]

encodeTypeKwarg :: Bool -> FilePath -> TypeKwarg -> Aeson.Value
encodeTypeKwarg normalize p k =
  Aeson.object
    [ "_node" .= aesText "TypeKwarg",
      "span" .= encodeSpan normalize p (tkSpan k),
      "name" .= aesText (tkName k),
      "value" .= encodeTypeKwVal normalize p (tkValue k)
    ]

encodeTypeKwVal :: Bool -> FilePath -> TypeKwargValue -> Aeson.Value
encodeTypeKwVal normalize p = \case
  TKVBudget b -> encodeBudgetArg normalize p b
  TKVQual q -> encodeQual normalize p q
  TKVExpr ex -> encodeExpr normalize p ex

encodeType :: Bool -> FilePath -> TypeExpr -> Aeson.Value
encodeType normalize p t =
  Aeson.object
    [ "_node" .= aesText "TypeRef",
      "span" .= encodeSpan normalize p (typeSpan t),
      "name" .= encodeQual normalize p (typeName t),
      "generics" .= map (encodeType normalize p) (typeGenerics t),
      "kwargs" .= map (encodeTypeKwarg normalize p) (typeKwargs t)
    ]

encodeArg :: Bool -> FilePath -> Arg -> Aeson.Value
encodeArg normalize p ar =
  Aeson.object
    [ "_node" .= aesText "Arg",
      "span" .= encodeSpan normalize p (argSpan ar),
      "name" .= case argName ar of Nothing -> Aeson.Null; Just n -> aesText n,
      "value" .= encodeExpr normalize p (argValue ar)
    ]

encodeParam :: Bool -> FilePath -> Param -> Aeson.Value
encodeParam normalize p pm =
  Aeson.object
    [ "_node" .= aesText "Param",
      "span" .= encodeSpan normalize p (paramSpan pm),
      "name" .= aesText (paramName pm),
      "type_annot" .= maybe Aeson.Null (encodeType normalize p) (paramTypeAnnot pm),
      "default" .= maybe Aeson.Null (encodeExpr normalize p) (paramDefault pm)
    ]

encodeExpr :: Bool -> FilePath -> Expr -> Aeson.Value
encodeExpr normalize p = \case
  ExprIntLit s i ->
    Aeson.object
      [ "_node" .= aesText "IntLit",
        "span" .= encodeSpan normalize p s,
        "value" .= i
      ]
  ExprFloatLit s d ->
    Aeson.object
      [ "_node" .= aesText "FloatLit",
        "span" .= encodeSpan normalize p s,
        "value" .= d
      ]
  ExprStrLit s v triple ->
    Aeson.object
      [ "_node" .= aesText "StringLit",
        "span" .= encodeSpan normalize p s,
        "value" .= aesText v,
        "triple" .= triple
      ]
  ExprBoolLit s bl ->
    Aeson.object
      [ "_node" .= aesText "BoolLit",
        "span" .= encodeSpan normalize p s,
        "value" .= bl
      ]
  ExprNullLit s ->
    Aeson.object
      [ "_node" .= aesText "NullLit",
        "span" .= encodeSpan normalize p s
      ]
  ExprIdent s n ->
    Aeson.object
      [ "_node" .= aesText "Identifier",
        "span" .= encodeSpan normalize p s,
        "name" .= aesText n
      ]
  ExprBudget b -> encodeBudgetArg normalize p b
  ExprBinOp b ->
    Aeson.object
      [ "_node" .= aesText "BinOp",
        "span" .= encodeSpan normalize p (bxSpan b),
        "op" .= aesText (bxOp b),
        "left" .= encodeExpr normalize p (bxLeft b),
        "right" .= encodeExpr normalize p (bxRight b)
      ]
  ExprUnaryOp u ->
    Aeson.object
      [ "_node" .= aesText "UnaryOp",
        "span" .= encodeSpan normalize p (uxSpan u),
        "op" .= aesText (uxOp u),
        "operand" .= encodeExpr normalize p (uxOperand u)
      ]
  ExprCall c ->
    Aeson.object
      [ "_node" .= aesText "Call",
        "span" .= encodeSpan normalize p (cllSpan c),
        "callee" .= encodeExpr normalize p (callee c),
        "args" .= map (encodeArg normalize p) (callArgs c)
      ]
  ExprMember m ->
    Aeson.object
      [ "_node" .= aesText "Member",
        "span" .= encodeSpan normalize p (mbSpan m),
        "obj" .= encodeExpr normalize p (mbObj m),
        "attr" .= aesText (mbAttr m)
      ]
  ExprIndex i ->
    Aeson.object
      [ "_node" .= aesText "Index",
        "span" .= encodeSpan normalize p (ixSpan i),
        "obj" .= encodeExpr normalize p (ixObj i),
        "index" .= encodeExpr normalize p (ixIndex i)
      ]
  ExprList l ->
    Aeson.object
      [ "_node" .= aesText "ListLit",
        "span" .= encodeSpan normalize p (lilSpan l),
        "items" .= map (encodeExpr normalize p) (lilItems l)
      ]
  ExprDict dict ->
    Aeson.object
      [ "_node" .= aesText "DictLit",
        "span" .= encodeSpan normalize p (dilSpan dict),
        "items"
          .= map
            (\(k, v) -> Aeson.Array (Vec.fromList [encodeExpr normalize p k, encodeExpr normalize p v]))
            (dilItems dict)
      ]
  ExprLambda lm ->
    Aeson.object
      [ "_node" .= aesText "Lambda",
        "span" .= encodeSpan normalize p (lamSpan lm),
        "params" .= map (encodeParam normalize p) (lamParams lm),
        "body" .= encodeExpr normalize p (lamBody lm)
      ]
  ExprSpawn s ->
    Aeson.object
      [ "_node" .= aesText "SpawnExpr",
        "span" .= encodeSpan normalize p (spSpan s),
        "agent" .= encodeCall normalize p (spAgent s)
      ]

encodeCall :: Bool -> FilePath -> Call_ -> Aeson.Value
encodeCall normalize p c = encodeExpr normalize p (ExprCall c)
