{-# LANGUAGE ApplicativeDo #-}
{-# LANGUAGE OverloadedStrings #-}

module Main (main) where

import qualified Data.Aeson as A
import qualified Data.ByteString.Lazy as BL
import qualified Data.Text as T
import qualified Data.Text.IO as TIO
import Options.Applicative
import System.Exit (exitFailure)

import Voss.IrStub (irStubValue)
import Voss.Json (encodeProgramUtf8)
import Voss.Parse (parseProgramText)

data Cmd = Ast {astPath :: FilePath, astNorm :: Bool} | Ir

main :: IO ()
main = execParser opts >>= run
  where
    opts =
      info (cmdP <**> helper) $
        fullDesc <> progDesc "Voss Haskell frontend (parser + AST JSON)"

    cmdP =
      subparser $
        command "ast" (info astP (progDesc "Parse .voss and print AST JSON"))
          <> command "ir" (info (pure Ir) (progDesc "Print experimental typed-IR stub JSON"))

    astP = do
      astPath <- strOption (long "path" <> metavar "FILE" <> help ".voss source file")
      astNorm <- switch (long "normalize-spans" <> help "Match Python to_dict(..., normalize_spans=True)")
      pure Ast {..}

run :: Cmd -> IO ()
run Ir = BL.putStr (A.encode irStubValue)
run Ast {astPath = path, astNorm = norm} = do
  (fp, src) <- case path of
    "-" -> (,) "<stdin>" <$> TIO.getContents
    _ -> (,) (T.pack path) <$> TIO.readFile path
  case parseProgramText fp src of
    Left err -> TIO.hPutStrLn stderr (T.pack err) >> exitFailure
    Right prog -> BL.putStr (encodeProgramUtf8 norm prog)
