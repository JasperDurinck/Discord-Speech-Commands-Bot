import wikipedia

def wikipedia_search(search_term):
    result = wikipedia.search(search_term)

    print(result[0])

    text = wikipedia.page(result[0]).summary
    print(text)
    return text