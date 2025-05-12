from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import LLMChain

def get_chat_chain(user_name: str = "", user_profile: str = ""):
    system_prompt_template = (
        "{user_profile} The user's name is {user_name}. You are a professional, helpful, and friendly assistant. "
        "Answer naturally, like a thoughtful human."
    )

    system_message = SystemMessagePromptTemplate.from_template(system_prompt_template)
    human_message = HumanMessagePromptTemplate.from_template("{input}")
    chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])

    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)

    return LLMChain(llm=llm, prompt=chat_prompt).partial(
        user_name=user_name,
        user_profile=user_profile
    )
