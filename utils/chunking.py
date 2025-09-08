def chunk_by_words(text, chunk_size=100):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def chunk_by_sentences(text):
    sentences = text.split(".")
    return [s.strip() + "." for s in sentences if s.strip()]
