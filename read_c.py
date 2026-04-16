import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

doc_ref = db.document("靜宜行銷/betty")
doc = doc_ref.get()
result = doc.to_dict()

keyword = "楊"
collection_ref = db.collection("靜宜資管")
docs = collection_ref.get()
for doc in docs:
	teacher = doc.to_dict()
	if keyword in teacher["name"]:
		print(teacher)