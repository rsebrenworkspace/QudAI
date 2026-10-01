import re

asm_path = r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll"
with open(asm_path, "rb") as f:
    data = f.read()

text = data.decode("latin1", errors="ignore")

for term in ["Stomach", "Campfire", "CampFire", "MakeCamp", "Butchery", "Harvestry", "CookingGameState", "CookingRecipe"]:
    matches = set(re.findall(rf"[A-Za-z0-9_.]*{term}[A-Za-z0-9_.]*", text))
    print(f"Term '{term}': {len(matches)} matches")
    for m in sorted(matches)[:10]:
        print(f"  {m}")
