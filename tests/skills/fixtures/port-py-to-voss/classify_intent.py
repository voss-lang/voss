def classify_intent(text):
    if "cancel" in text:
        return "cancel"
    return "unknown"
