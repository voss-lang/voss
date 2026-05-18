{-# LANGUAGE DuplicateRecordFields #-}

module Ast (
  Span (..),
  Program (..),
  Stmt (..),
  Decl (..),
  Expr (..),
  TypeExpr (..),
  Pattern (..),
  NodeSpan (nodeSpan),
  QualName (..),
  BudgetArg (..),
  BudgetNum (..),
  TypeKwarg (..),
  Arg (..),
  Param (..),
  ConfidenceGate (..),
  MatchCase (..),
  Decorator (..),
  AgentOptions (..),
  ClassField (..),
) where

import Data.Text (Text)

-- | Source span matching Python Lark @ propagate_positions ranges (lines/cols are 1-based).
data Span = Span
  { spanFile :: !FilePath,
    spanLineStart :: !Int,
    spanColStart :: !Int,
    spanLineEnd :: !Int,
    spanColEnd :: !Int,
    spanSynthetic :: !Bool
  }
  deriving (Eq, Show)

class NodeSpan n where
  nodeSpan :: n -> Span

instance NodeSpan Span where
  nodeSpan = id

instance NodeSpan Program where
  nodeSpan = programSpan

data Program = Program
  { programSpan :: !Span,
    body :: ![Stmt]
  }
  deriving (Eq, Show)

instance NodeSpan Stmt where
  nodeSpan = stmtSpan

data Stmt
  = StmtExpr StmtExpr_
  | StmtLet LetStmt_
  | StmtIf IfStmt_
  | StmtMatch MatchStmt_
  | StmtCtx CtxStmt_
  | StmtWithin WithinStmt_
  | StmtTry TryStmt_
  | StmtReturn ReturnStmt_
  | StmtYield YieldStmt_
  | StmtInclude IncludeStmt_
  | StmtFn FnDecl_
  | StmtAgent AgentDecl_
  | StmtPrompt PromptDecl_
  | StmtClass ClassDecl_
  | StmtUse UseStmt_
  deriving (Eq, Show)

stmtSpan :: Stmt -> Span
stmtSpan = \case
  StmtExpr x -> sxSpan x
  StmtLet x -> lsSpan x
  StmtIf x -> ifsSpan x
  StmtMatch x -> msSpan x
  StmtCtx x -> cxSpan x
  StmtWithin x -> wfSpan x
  StmtTry x -> tcSpan x
  StmtReturn x -> rsSpan x
  StmtYield x -> ysSpan x
  StmtInclude x -> isSpan x
  StmtFn x -> fnSpan x
  StmtAgent x -> agSpan x
  StmtPrompt x -> prSpan x
  StmtClass x -> clSpan x
  StmtUse x -> usSpan x

declSpan :: Stmt -> Span
declSpan = stmtSpan

data StmtExpr_ = StmtExpr_
  { sxSpan :: !Span,
    sxExpr :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan StmtExpr_ where
  nodeSpan = sxSpan

data LetStmt_ = LetStmt_
  { lsSpan :: !Span,
    lsName :: !Text,
    lsTypeAnnot :: !(Maybe TypeExpr),
    lsValue :: !(Maybe Expr)
  }
  deriving (Eq, Show)

instance NodeSpan LetStmt_ where
  nodeSpan = lsSpan

data IfStmt_ = IfStmt_
  { ifsSpan :: !Span,
    ifsCondition :: !IfCondition,
    ifsThen :: ![Stmt],
    ifsElse :: !(Maybe [Stmt])
  }
  deriving (Eq, Show)

instance NodeSpan IfStmt_ where
  nodeSpan = ifsSpan

-- | Parsed @if@ condition slot: ordinary expression or confidence gate (@ p ...)
data IfCondition
  = IfCondExpr !Expr
  | IfCondGate !ConfidenceGate_
  deriving (Eq, Show)

data ConfidenceGate_ = ConfidenceGate_
  { cgSpan :: !Span,
    cgTarget :: !Expr,
    cgOp :: !Text,
    cgThreshold :: !Double
  }
  deriving (Eq, Show)

instance NodeSpan ConfidenceGate_ where
  nodeSpan = cgSpan

data MatchStmt_ = MatchStmt_
  { msSpan :: !Span,
    msScrutinee :: !Expr,
    msCases :: ![MatchCase_],
    msThreshold :: !(Maybe Double)
  }
  deriving (Eq, Show)

instance NodeSpan MatchStmt_ where
  nodeSpan = msSpan

data MatchCase_ = MatchCase_
  { mcSpan :: !Span,
    mcPattern :: !Pattern,
    mcBody :: ![Stmt]
  }
  deriving (Eq, Show)

instance NodeSpan MatchCase_ where
  nodeSpan = mcSpan

data CtxStmt_ = CtxStmt_
  { cxSpan :: !Span,
    cxBudget :: !BudgetArg,
    cxBody :: ![Stmt]
  }
  deriving (Eq, Show)

instance NodeSpan CtxStmt_ where
  nodeSpan = cxSpan

data WithinStmt_ = WithinStmt_
  { wfSpan :: !Span,
    wfBudgetArgs :: ![BudgetArg],
    wfPrimary :: ![Stmt],
    wfFallback :: !(Maybe [Stmt])
  }
  deriving (Eq, Show)

instance NodeSpan WithinStmt_ where
  nodeSpan = wfSpan

data TryStmt_ = TryStmt_
  { tcSpan :: !Span,
    tcTryBody :: ![Stmt],
    tcExcName :: !(Maybe Text),
    tcCatchBody :: ![Stmt]
  }
  deriving (Eq, Show)

instance NodeSpan TryStmt_ where
  nodeSpan = tcSpan

data ReturnStmt_ = ReturnStmt_
  { rsSpan :: !Span,
    rsValue :: !(Maybe Expr)
  }
  deriving (Eq, Show)

instance NodeSpan ReturnStmt_ where
  nodeSpan = rsSpan

data YieldStmt_ = YieldStmt_
  { ysSpan :: !Span,
    ysValue :: !(Maybe Expr)
  }
  deriving (Eq, Show)

instance NodeSpan YieldStmt_ where
  nodeSpan = ysSpan

data IncludeStmt_ = IncludeStmt_
  { isSpan :: !Span,
    isValue :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan IncludeStmt_ where
  nodeSpan = isSpan

data FnDecl_ = FnDecl_
  { fnSpan :: !Span,
    fnName :: !Text,
    fnParams :: ![Param],
    fnReturn :: !(Maybe TypeExpr),
    fnBody :: ![Stmt],
    fnDecorators :: ![Decorator]
  }
  deriving (Eq, Show)

instance NodeSpan FnDecl_ where
  nodeSpan = fnSpan

data AgentDecl_ = AgentDecl_
  { agSpan :: !Span,
    agName :: !Text,
    agParams :: ![Param],
    agReturn :: !(Maybe TypeExpr),
    agOptions :: !AgentOptions,
    agBody :: ![Stmt],
    agDecorators :: ![Decorator]
  }
  deriving (Eq, Show)

instance NodeSpan AgentDecl_ where
  nodeSpan = agSpan

data PromptDecl_ = PromptDecl_
  { prSpan :: !Span,
    prName :: !Text,
    prExtends :: !(Maybe QualName),
    prBody :: ![PromptStringLit],
    prDecorators :: ![Decorator]
  }
  deriving (Eq, Show)

instance NodeSpan PromptDecl_ where
  nodeSpan = prSpan

-- | Stored like Python body: sequences of prompt string literals.
data PromptStringLit = PromptStringLit
  { pslSpan :: !Span,
    pslValue :: !Text,
    pslTriple :: !Bool
  }
  deriving (Eq, Show)

data ClassDecl_ = ClassDecl_
  { clSpan :: !Span,
    clName :: !Text,
    clFields :: ![ClassField],
    clDecorators :: ![Decorator]
  }
  deriving (Eq, Show)

instance NodeSpan ClassDecl_ where
  nodeSpan = clSpan

data UseStmt_ = UseStmt_
  { usSpan :: !Span,
    usPath :: ![Text],
    usAlias :: !(Maybe Text)
  }
  deriving (Eq, Show)

instance NodeSpan UseStmt_ where
  nodeSpan = usSpan

-- | Convenience alias grouping declaration shapes (already represented as Stmt in Python).
type Decl = Stmt

data BudgetNum
  = BNInt !Integer
  | BNFloat !Double
  deriving (Eq, Show)

instance NodeSpan BudgetArg where
  nodeSpan = budgetSpan

data BudgetArg = BudgetArg
  { budgetSpan :: !Span,
    budgetKwName :: !Text,
    budgetUnit :: !Text,
    budgetValue :: !BudgetNum,
    budgetRaw :: !Text
  }
  deriving (Eq, Show)

data QualName = QualName
  { qnSpan :: !Span,
    qnParts :: ![Text]
  }
  deriving (Eq, Show)

instance NodeSpan QualName where
  nodeSpan = qnSpan

data TypeKwarg = TypeKwarg
  { tkSpan :: !Span,
    tkName :: !Text,
    tkValue :: !TypeKwargValue
  }
  deriving (Eq, Show)

instance NodeSpan TypeKwarg where
  nodeSpan = tkSpan

-- | Mirrors Python loosely-typed Node in TypeKwarg.value.
data TypeKwargValue
  = TKVBudget !BudgetArg
  | TKVQual !QualName
  | TKVExpr !Expr
  deriving (Eq, Show)

instance NodeSpan TypeExpr where
  nodeSpan = typeSpan

data TypeExpr = TypeExpr
  { typeSpan :: !Span,
    typeName :: !QualName,
    typeGenerics :: ![TypeExpr],
    typeKwargs :: ![TypeKwarg]
  }
  deriving (Eq, Show)

instance NodeSpan Param where
  nodeSpan = paramSpan

data Param = Param
  { paramSpan :: !Span,
    paramName :: !Text,
    paramTypeAnnot :: !(Maybe TypeExpr),
    paramDefault :: !(Maybe Expr)
  }
  deriving (Eq, Show)

instance NodeSpan Arg where
  nodeSpan = argSpan

data Arg = Arg
  { argSpan :: !Span,
    argName :: !(Maybe Text),
    argValue :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan Decorator where
  nodeSpan = decSpan

data Decorator = Decorator
  { decSpan :: !Span,
    decName :: !Text,
    decArgs :: ![Arg]
  }
  deriving (Eq, Show)

data AgentOptions = AgentOptions
  { aoSpan :: !Span,
    aoSystem :: !(Maybe Expr),
    aoTools :: !(Maybe Expr),
    aoModel :: !(Maybe Expr),
    aoRetries :: !(Maybe Expr),
    aoMemory :: !(Maybe Expr)
  }
  deriving (Eq, Show)

instance NodeSpan AgentOptions where
  nodeSpan = aoSpan

data ClassField = ClassField
  { cfSpan :: !Span,
    cfName :: !Text,
    cfType :: !TypeExpr,
    cfDefault :: !(Maybe Expr)
  }
  deriving (Eq, Show)

instance NodeSpan ClassField where
  nodeSpan = cfSpan

instance NodeSpan Pattern where
  nodeSpan = patternSpan

data Pattern
  = PatSimilar SimilarPat_
  | PatWildcard !Span
  | PatExpr ExprPat_
  deriving (Eq, Show)

patternSpan :: Pattern -> Span
patternSpan = \case
  PatSimilar x -> ssSpan x
  PatWildcard s -> s
  PatExpr x -> epsSpan x

data SimilarPat_ = SimilarPat_
  { ssSpan :: !Span,
    ssText :: !Text
  }
  deriving (Eq, Show)

instance NodeSpan SimilarPat_ where
  nodeSpan = ssSpan

data ExprPat_ = ExprPat_
  { epsSpan :: !Span,
    epsExpr :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan ExprPat_ where
  nodeSpan = epsSpan

instance NodeSpan Expr where
  nodeSpan = exprSpan

data Expr
  = ExprIntLit !Span !Integer
  | ExprFloatLit !Span !Double
  | ExprStrLit !Span !Text !Bool
  | ExprBoolLit !Span !Bool
  | ExprNullLit !Span
  | ExprIdent !Span !Text
  | ExprBudget !BudgetArg
  | ExprBinOp !BinOp_
  | ExprUnaryOp !UnaryOp_
  | ExprCall !Call_
  | ExprMember !Member_
  | ExprIndex !Index_
  | ExprList !ListLit_
  | ExprDict !DictLit_
  | ExprLambda !Lambda_
  | ExprSpawn !Spawn_
  deriving (Eq, Show)

exprSpan :: Expr -> Span
exprSpan = \case
  ExprIntLit s _ -> s
  ExprFloatLit s _ -> s
  ExprStrLit s _ _ -> s
  ExprBoolLit s _ -> s
  ExprNullLit s -> s
  ExprIdent s _ -> s
  ExprBudget b -> budgetSpan b
  ExprBinOp x -> bxSpan x
  ExprUnaryOp x -> uxSpan x
  ExprCall x -> cllSpan x
  ExprMember x -> mbSpan x
  ExprIndex x -> ixSpan x
  ExprList x -> lilSpan x
  ExprDict x -> dilSpan x
  ExprLambda x -> lamSpan x
  ExprSpawn x -> spSpan x

data BinOp_ = BinOp_
  { bxSpan :: !Span,
    bxOp :: !Text,
    bxLeft :: !Expr,
    bxRight :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan BinOp_ where
  nodeSpan = bxSpan

data UnaryOp_ = UnaryOp_
  { uxSpan :: !Span,
    uxOp :: !Text,
    uxOperand :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan UnaryOp_ where
  nodeSpan = uxSpan

data Call_ = Call_
  { cllSpan :: !Span,
    callee :: !Expr,
    callArgs :: ![Arg]
  }
  deriving (Eq, Show)

instance NodeSpan Call_ where
  nodeSpan = cllSpan

data Member_ = Member_
  { mbSpan :: !Span,
    mbObj :: !Expr,
    mbAttr :: !Text
  }
  deriving (Eq, Show)

instance NodeSpan Member_ where
  nodeSpan = mbSpan

data Index_ = Index_
  { ixSpan :: !Span,
    ixObj :: !Expr,
    ixIndex :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan Index_ where
  nodeSpan = ixSpan

data ListLit_ = ListLit_
  { lilSpan :: !Span,
    lilItems :: ![Expr]
  }
  deriving (Eq, Show)

instance NodeSpan ListLit_ where
  nodeSpan = lilSpan

data DictLit_ = DictLit_
  { dilSpan :: !Span,
    dilItems :: ![(Expr, Expr)]
  }
  deriving (Eq, Show)

instance NodeSpan DictLit_ where
  nodeSpan = dilSpan

data Lambda_ = Lambda_
  { lamSpan :: !Span,
    lamParams :: ![Param],
    lamBody :: !Expr
  }
  deriving (Eq, Show)

instance NodeSpan Lambda_ where
  nodeSpan = lamSpan

data Spawn_ = Spawn_
  { spSpan :: !Span,
    spAgent :: !Call_
  }
  deriving (Eq, Show)

instance NodeSpan Spawn_ where
  nodeSpan = spSpan
