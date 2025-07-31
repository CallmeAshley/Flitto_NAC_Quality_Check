# prompt_builder/build_category_prompt.py

def build_category_prompt(sentence: str):
    system_msg = {
        "role": "system",
        "content": (
            "You are a localization quality checker AI.\n"
            "Your task is to identify which formatting categories are present in a given translated sentence.\n"
            "The only valid categories are: currency, date, numeric, time.\n"
            "Only return the category if a clear formatting pattern appears in the sentence.\n"
            "Do NOT infer based on meaning or context.\n"
            "If no formatting is detected, return an empty list [].\n"
            "Return format: a JSON list of strings. Example: [\"currency\"] or [\"numeric\", \"date\"] or []."
        )
    }
    user_msg = {
        "role": "user",
        "content": f"Translated sentence: {sentence}\n\nWhich categories apply?"
    }
    return system_msg, user_msg


# prompt_builder/build_check_prompt.py

def build_check_prompt(sentence: str, guideline: str, source_text: str):
    system_msg = {
        "role": "system",
        "content": (
            "You are a localization format validator AI.\n"
            "Your task is to check whether the translated sentence conforms to the following locale-specific guideline.\n"
            "If the sentence violates the guideline, suggest a corrected version.\n"
            "If no changes are needed, return the original sentence.\n"
            "You will also receive the source sentence to help compare formatting differences.\n"
            "Do not remove or modify any numbering, bullets, or structural punctuation marks such as: a), 1., (1), •, - \n"
            "These elements must be preserved exactly as they appear. \n"
            "Do not change the meaning or add explanations. Return only the revised sentence."
        )
    }
    user_msg = {
        "role": "user",
        "content": (
            f"Guideline:\n{guideline}\n\n"
            f"Source sentence:\n{source_text.strip()}\n\n"
            f"Translated sentence:\n{sentence.strip()}\n\n"
            "Revised translation:"
        )
    }
    return system_msg, user_msg
