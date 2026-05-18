-- | Voss surface parse (.voss → 'Program').
--
-- Phase 3: Megaparsec port of 'voss/grammar.lark' is in progress. The executable
-- and JSON pipeline are in place; implement 'pProgram' here and remove the stub.

module Voss.Parse (parseProgramText) where

import Data.Text (Text)
import qualified Data.Text as T

import Voss.Ast (Program)
import Voss.Span

parseProgramText :: Text -> Text -> Either String Program
parseProgramText fp _src =
  Left $
    "Haskell parser stub: set VOSS_FRONTEND=python (default) or implement Voss.Parse (see frontend-hs/README.md). file="
      ++ T.unpack fp
