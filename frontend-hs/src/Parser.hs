{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE OverloadedStrings #-}

module Parser (
  parseProgram,
) where

import Ast
import Control.Monad (void)
import qualified Data.Char as Char
import Data.Text (Text)
import qualified Data.Text as T
import Data.Void (Void)
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
-- WS / trivia

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
stmtSep = hj *> fills *> void (some eoline) *> hj *> fills

------------------------------------------------------------------------------
-- Positions

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
keyword k = hj *> Mp.chunk k *> kwBoundary

symbolic :: Text -> P ()
symbolic sym = hj *> Mp.chunk sym

------------------------------------------------------------------------------
-- Identifier

identLetter :: Char -> Bool
identLetter c = Char.isAlpha c || c == '_'

identCont :: Char -> Bool
identCont c = Char.isAlphaNum c || c == '_'

identTok :: P Text
identTok = do
  c <- satisfy identLetter
  cs <- Mp.many (satisfy identCont)
  let t = T.pack (c : cs)
  if t == "similar"
    then fail "similar keyword"
    else
      if t == "_"
        then fail "underscore pattern"
        else pure t

simKeyword :: P ()
simKeyword = hj *> Mp.chunk "similar" *> kwBoundary

underscoreKw :: P ()
underscoreKw = hj *> Mp.chunk "_" *> kwBoundary

------------------------------------------------------------------------------
-- Strings (Python-aligned)

simpleEsc :: Char -> Maybe Char
simpleEsc =
  flip lookup
    [ ('"', '\"'),
      (''', '\''),
      ('\\', '\\'),
      ('a', '\a'),
      ('b', '\b'),
      ('f', '\f'),
      ('n', '\n'),
      ('r', '\r'),
      ('t', '\t'),
      ('v', '\v')
    ]

readOct :: Int -> Char -> [(Char, Int)] -> (Char, Int)
readOct digits cur acc =
  if digits <= 0
    then (Char.chr (go (reverse acc) 0), 0)
    else
      if cur >= '0' && cur <= '7'
        then readOct (pred digits) '\0' ((cur, 0) : acc)
        else (Char.chr (go (reverse acc) 0), digits)
 where
  go [] n = n
  go ((d, _) : ds) n = go ds (n * 8 + fromEnum d - fromEnum '0')

decodeEscaped :: String -> String
decodeEscaped s = go 0 ""
 where
  go i acc
    | i >= length s = acc
    | otherwise =
        let ch = s !! i
         in if ch /= '\\'
              then go (i + 1) (acc ++ [ch])
              else
                if i + 1 >= length s
                  then go (i + 1) (acc ++ ['\\'])
                  else
                    let e = s !! (i + 1)
                     in case simpleEsc e of
                          Just o -> go (i + 2) (acc ++ [o])
                          Nothing
                            | e >= '0' && e <= '7' ->
                                let digs = takeWhile (\c -> c >= '0' && c <= '7') (drop (i + 1) s)
                                    ln = length digs
                                    v = fst (readOct ln '\0' (zip digs (repeat 0))) -- misuse
                                    -- Fixed below with proper numeric parse per Python
                                 in undefined
                            | e == 'x' || e == 'u' || e == 'U' -> undefined -- filled next patch
                          | otherwise -> go (i + 2) (acc ++ ['\\', e])
