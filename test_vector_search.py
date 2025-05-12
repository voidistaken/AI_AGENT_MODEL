import numpy as np
from utils.vector_utils import insert_or_update_embedding, search_similar_embeddings

embedding = np.random.rand(1536).astype(np.float32)

# Test insert
insert_or_update_embedding("user1", "bio", "This is updated bio", embedding)

results = search_similar_embeddings(embedding)
for r in results:
    print(r)
