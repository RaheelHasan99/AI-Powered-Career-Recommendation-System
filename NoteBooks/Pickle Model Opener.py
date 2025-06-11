import pickle
with open("career_vectorizer.pkl", "rb") as f:
    model = pickle.load(f)


print("Type of model:", model)