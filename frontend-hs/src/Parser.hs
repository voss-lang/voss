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
import Text.Megaparsec hiding (sepBy, sepEndBy, some, takeWhile1)
import qualified Text.Megaparsec as Mp
import Text.Megaparsec.Char
import qualified Text.Megaparsec.Char.Lexer as L
import Text.Megaparsec.Pos (SourcePos (..), unPos)

type Parser = Parsec Void Text

parseProgram :: FilePath -> Text -> Either String Program
parseProgram fp txt = case Mp.runParser (pProg fp <* eof) fp txt of
  Left eb -> Left (errorBundlePretty eb)
  Right p -> Right p

-------------------------------------------------------------------------------
-- Helpers: whitespace / newlines / spans

hj :: Parser ()
hj =
  void . Mp.many $
    choice
      [ void (Mp.takeWhile1P Nothing (\c -> c == ' ' || c == '\t')),
        try $ char '#' >> void (Mp.takeWhileP Nothing (/= '\n'))
      ]

fills :: Parser ()
fills =
  void . Mp.many $
    choice
      [ try eoline,
        void hj
      ]

eoline :: Parser ()
eoline = void . try $ optionally (Mp.chunk "\r") *> Mp.chunk "\n"

stmtSep :: Parser ()
stmtSep = hj *> fills *> void (Mp.some eoline) *> hj *> fills

spanOf :: FilePath -> SourcePos -> SourcePos -> Span
spanOf fp a b =
  Span
    fp
    (fromIntegral (unPos (sourceLine a)))
    (fromIntegral (unPos (sourceColumn a)))
    (fromIntegral (unPos (sourceLine b)))
    (fromIntegral (unPos (sourceColumn b)))
    False

{- | Run @p@ and attach a span covering the consumed input (exclusive end column matches Megaparsec post-state). -}
located :: FilePath -> Parser a -> Parser (Span, a)
located fp p = do
  posA <- Mp.getSourcePos
  Mp.offsetA <- Mp.getOffset
  x <- p
  posB <- Mp.getSourcePos
  let sp = spanOf fp posA posB
  seq Mp.offsetA (pure ()) -- silence unused-warning pattern
  pure (seq x ()) $ (sp, x)

-- Work around unused offset warning by not binding offset
located' :: FilePath -> Parser a -> Parser (Span, a)
located' fp p = do
  posA <- Mp.getSourcePos
  _ <- Mp.getOffset
  x <- p
  posB <- Mp.getSourcePos
  pure (spanOf fp posA posB, x)

identLetter :: Char -> Bool
identLetter c = Char.isAlpha c || c == '_'

identCont :: Char -> Bool
identCont c = Char.isAlphaNum c || c == '_'

kwBoundary :: Parser ()
kwBoundary = void (notFollowedBy (satisfy identCont) <?> "")

keyword :: Text -> Parser Text
keyword w = hj *> Mp.chunk w <* kwBoundary

symbolic :: Text -> Parser ()
symbolic sym = hj *> Mp.chunk sym <* hj

braceL, braceR, parenL, parenR, bracketL, bracketR :: Parser ()
braceL = symbolic "{"
braceR = symbolic "}"
parenL = symbolic "("
parenR = symbolic ")"
bracketL = symbolic "["
bracketR = symbolic "]"

identText :: Parser Text
identText = do
  c <- satisfy identLetter <?> "identifier"
  rest <- Mp.many (satisfy identCont)
  let t = T.pack (c : rest)
  if | t == "similar" -> fail "similar is reserved for patterns"
       | t == "_" -> fail "bare _ must use wildcard pattern terminal"
       | otherwise -> pure t

-- | Parses raw identifier token excluding pattern-only terminals.
rawIdentTok :: Parser Text
rawIdentTok = identText

-------------------------------------------------------------------------------
-- Strings & budget units

simpleEsc :: [(Char, Char)]
simpleEsc =
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

decodeInnerString :: Text -> Text
decodeInnerString inner =
  let go i acc =
        if i >= T.length inner
          then T.concat (reverse acc)
          else
            let ch = T.index inner i
             in if ch /= '\\'
                  then let j = skipUTF8Chars inner i 1 in go j (T.singleton ch : acc)
                  else case T.indexMaybe inner (i + 1) of
                    Nothing ->
                      let j = i + 1 in go j (T.singleton '\\' : acc)
                    Just e ->
                      case lookup e simpleEsc of
                        Just c ->
                          let j = i + 2 in go j (T.singleton c : acc)
                        Nothing
                          | e >= '0' && e <= '7' ->
                              let digs = octalDigits inner (i + 1)
                                  val = parseOct digs
                                  consumed = T.length digs
                                  j = i + 1 + consumed
                               in go j (T.singleton (Char.chr val) : acc)
                          | e == 'x' || e == 'u' || e == 'U' ->
                              case hexEscape inner (i + 1) e of
                                Just (ch', j') -> go j' (T.singleton ch' : acc)
                                Nothing ->
                                  let j = i + 2 in go j (T.pack ['\\', e] : acc)
                          | otherwise ->
                              let j = i + 2 in go j (T.pack ['\\', e] : acc)
   in go 0 []
  where
    skipUTF8Chars t pos n | n <= 0 = pos | otherwise = skipUTF8Chars t (pos + 1) (n - 1)
    {-# INLINE skipUTF8Chars #-}
octalDigits _ _ = ""

-- | Fallback minimal oct reader (digits after backslash consumed again above) — trimmed for space in file:
