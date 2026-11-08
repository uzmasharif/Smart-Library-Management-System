
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def recommend_books(topic, books):

    if not topic.strip() or not books:
        return []

    book_descriptions = []

    for book in books:
        description = (
            str(book["title"]) + " " +
            str(book["author"]) + " " +
            str(book["category"])
        )

        book_descriptions.append(description)

    all_text = book_descriptions + [topic]

    vectorizer = TfidfVectorizer(stop_words="english")

    try:
        tfidf_matrix = vectorizer.fit_transform(all_text)
    except ValueError:
        return []

    similarity_scores = cosine_similarity(
        tfidf_matrix[-1],
        tfidf_matrix[:-1]
    ).flatten()

    recommendations = []

    for index, score in enumerate(similarity_scores):
        if score > 0:
            recommendations.append({
                "book": books[index],
                "score": round(float(score) * 100, 2)
            })

    recommendations.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return recommendations[:5]
