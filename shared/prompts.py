"""
Templates de prompts versionnés (PRD QLT-1.1).
Réponse conditionnée au contexte — "je ne sais pas" si insuffisant (PRD QLT-2.1).
"""
from langchain_core.prompts import ChatPromptTemplate

RAG_PROMPT_V1 = ChatPromptTemplate.from_messages([
    ("system", """Tu es un assistant qui répond uniquement à partir du contexte fourni.
Si le contexte ne contient pas l'information nécessaire pour répondre, dis clairement "Je ne sais pas" ou "Ce n'est pas dans le contexte fourni."
N'invente rien. Cite les sources quand c'est pertinent."""),
    ("human", """Contexte (extraits de Notion) :
{context}

Question : {question}

Réponse (basée uniquement sur le contexte ci-dessus) :"""),
])

# Pour évolution future : RAG_PROMPT_V2 = ...

def get_rag_prompt(version: str = "v1") -> ChatPromptTemplate:
    if version == "v1":
        return RAG_PROMPT_V1
    return RAG_PROMPT_V1
