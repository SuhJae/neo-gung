# This is a file to sync the language files (utility)
import deepl
import json

translator = deepl.Translator("e696d34b-262a-e2fe-9aa0-b1577eec98a7:fx")
lang_dir = "assets/lang/"

original_lang = "en"
target_lang = ["ko", "ja", "zh", "es"]

with open(lang_dir + original_lang + ".json", "r", encoding="utf-8") as f:
    original_lang_json = json.loads(f.read())

for lang in target_lang:
    print(f"Syncing {lang}...")
    # check if there is a element missing (all text are flattened)
    with open(lang_dir + lang + ".json", "r", encoding="utf-8") as f:
        target_lang_json = json.loads(f.read())

    for key in original_lang_json:
        if key not in target_lang_json:
            print(f"Missing key: {key}")
            target_lang_json[key] = translator.translate_text(source_lang=original_lang, target_lang=lang,
                                                              text=original_lang_json[key]).text

    with open(lang_dir + lang + ".json", "w", encoding="utf-8") as f:
        f.write(json.dumps(target_lang_json, indent=4, ensure_ascii=False))
