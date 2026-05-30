import os
import re

def remove_emojis(text):
    # This regex covers a large range of emojis
    emoji_pattern = re.compile(
        "["
        "\U0001f300-\U0001f6ff"  # Miscellaneous Symbols and Pictographs
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U00002600-\U000026ff"  # Miscellaneous Symbols
        "\U00002700-\U000027bf"  # Dingbats
        "\U0001f1e0-\U0001f1ff"  # Flags
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def process_files():
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(('.md', '.txt')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = remove_emojis(content)
                    
                    if content != new_content:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Cleaned {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    process_files()
