# prompt_builder/build_semantic_check_prompt.py

# prompt_builder/build_prompt.py

def _base_user_block(source: str, translated: str) -> str:
    return (
        f"Source:\n{source.strip()}\n\n"
        f"Translation:\n{translated.strip()}\n\n"
        "Evaluate and return the result."
    )

def build_emoji_check_prompt(source: str, translated: str):
    system_msg = {
        "role": "system",
        "content": (
            "You are a localization QA AI focusing ONLY on emoji consistency.\n"
            "If any emoji is moved, reordered, or placed in a different part of the sentence than in the source, this must be flagged as an issue.\n" 
            "Ignore words, punctuation, and formatting — look ONLY at emojis (including ZWJ sequences, skin tones).\n"
            "Return strictly in this format:\n"
            "{\n"
            "  \"emoji_issue\": true|false,\n"
            "  \"reasons\": [\"short reason\" ...],\n"
            "  \"suggestions\": [\"corrected translation string only\" ...]\n"
            "}\n"
            "- If emoji_issue is true, the suggestions MUST be the final translation text itself (no meta words like 'Include', 'Add', or explanations).\n"
            "- If false, reasons must be []. Do not propose fixes."
        )
    }
    user_msg = {"role": "user", "content": _base_user_block(source, translated)}
    return system_msg, user_msg

def build_missing_check_prompt(source: str, translated: str):
    system_msg = {
        "role": "system",
        "content": (
            "You are a localization QA AI focusing ONLY on missing content.\n"
            "Flag true if ANY unit of meaning in the source is absent in the translation "
            "(word, number, name, interjection, clause). Minor reordering is okay as long as meaning is preserved.\n"
            "Return strictly in this format:\n"
            "{\n"
            "  \"missing_content\": true|false,\n"
            "  \"missing_spans\": [\"exact source fragment that appears missing\" ...],\n"
            "  \"reasons\": [\"short reason\" ...],\n"
            "  \"suggestions\": [\"corrected translation string only\" ...]\n"
            "}\n"
            "- If missing_content is true, the suggestion MUST be the final translation text itself (no 'Include', 'Add', or any explanation).\n"
            "- If false, arrays must be []. Do not propose fixes."
        )
    }
    user_msg = {"role": "user", "content": _base_user_block(source, translated)}
    return system_msg, user_msg

def build_addition_check_prompt(source: str, translated: str):
    system_msg = {
        "role": "system",
        "content": (
            "You are a localization QA AI focusing ONLY on added/altered meaning (faithfulness).\n"
            "Flag true when the translation inserts or modifies content not present in the source.\n"
            "Classify severity:\n"
            "- mild: small stylistic intensifiers/adverbs/adjectives that slightly extend tone/scope.\n"
            "- severe: added phrases/claims/greetings or changes that alter the meaning.\n"
            "Return strictly in this format:\n"
            "{\n"
            "  \"faithfulness_issue\": true|false,\n"
            "  \"faithfulness_type\": \"none\"|\"mild\"|\"severe\",\n"
            "  \"added_spans\": [\"exact translation fragment that seems added\" ...],\n"
            "  \"reasons\": [\"short reason\" ...],\n"
            "  \"suggestions\": [\"corrected translation string only\" ...]\n"
            "}\n"
            "- If faithfulness_issue is true, the suggestion MUST be the final translation text itself (no 'Remove', 'Delete', 'Replace', or explanations).\n"
            "- If false, type must be \"none\" and arrays must be []. Do not propose fixes."
        )
    }
    user_msg = {"role": "user", "content": _base_user_block(source, translated)}
    return system_msg, user_msg




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
            "You will also receive the source sentence to help you understand the context and intended meaning of the translated sentence.\n"
            "Do not remove or modify any numbering, bullets, or structural markers in the sentence such as: a), 1., (1), •, '- ', ➔, →, *, <, > , [, ], .., :, ; #, !, -, >, ] , etc. These elements must be preserved exactly as they appear in the source sentence.\n"
            "These elements must be preserved exactly as they appear. \n"
            "Do not change the meaning or add explanations. Return only the revised sentence.\n"
            "Do not omit, rephrase, or summarize any semantically meaningful component of the original translation, including but not limited to modifiers, qualifiers, references, or ownership indicators.\n" 
            "All content must be preserved as-is unless it clearly violates locale formatting or results in unnaturalness in the target language.\n"
            "**Context-Aware Formatting Principle**\n"
            "**LLM must always consider the grammatical and semantic context of the sentence before applying guidelines.**\n"
            "Even when a formatting rule in the guideline is clearly defined, it must not override the natural word order or fluency of the target language.\n"
            "If the formatting rule in the guideline creates an unnatural expression in the target language, adjust the position or structure accordingly while preserving the original meaning and locale format type.\n"
            "Important: The revised sentence must be exactly the same as the original translated sentence, except for the parts where locale formatting has been corrected\n"
            "If the translated sentence contains any emojis like ✅, ❌, ❗, ❓, ✔️, never delete or move them from their original position.\n"
            "Preserve commonly accepted market abbreviations such as K, M, B (e.g., $600K, 1M €) if they are contextually appropriate and clear.\n"
            "Do not modify the ending punctuation of the sentence.\n"
            "If the source sentence ends with a colon (:), comma (,), ellipsis (..), regular space, or any other non-period character, preserve it as-is."
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
