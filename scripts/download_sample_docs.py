import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config
from utils.logger import get_logger

logger = get_logger("setup_sample_docs")

TOMATO_GUIDE = """ICAR Tomato Disease and Management Guide
Version 2.4 - Farmer Advisory

Tomato Yellow Leaf Curl Virus (TYLCV) Symptoms:
TYLCV is a devastating virus transmitted by whiteflies (Bemisia tabaci). Infected tomato plants show severe stunting, erect growth habit, and marked reduction in leaf size. The leaves curl upwards and inwards, resembling small cups. Leaf margins display strong yellowing (chlorosis). If plants are infected early, fruit yield can drop by 100%.

Prevention and Management of TYLCV:
1. Whitefly Control: Install yellow sticky traps (15-20 traps per acre) to monitor and capture adult whiteflies. Apply systemic insecticides like Imidacloprid (0.5 ml/litre of water) or spray neem oil (1% concentration) to repel vectors.
2. Net Barriers: Raise tomato nursery beds under 40-mesh insect-proof nylon nets to prevent early infestation.
3. Clean Cultivation: Remove and destroy infected volunteer tomato plants and weeds in the vicinity which act as viral reservoirs.
4. Resistant Cultivars: Use certified hybrid seed varieties with TYLCV resistance (e.g., Arka Rakshak, Abhinav).
"""

RICE_BLAST_MANUAL = """KVK Rice Disease Advisory - Rice Blast Control
Document ID: R-BLAST-2026

Rice Blast Disease Symptoms:
Rice Blast (caused by Magnaporthe oryzae) affects all aboveground parts of the rice plant. The most characteristic symptoms are spindle-shaped (eye-shaped) lesions on the leaves, with grayish centers and brown borders. Lesions can coalesce and destroy the entire leaf blade. In 'neck blast', the pathogen attacks the neck node of the panicle, turning it blackish-purple and causing the panicle to fall over, leading to empty grains.

Management Strategies for Rice Blast:
- Cultivar Selection: Plant resistant varieties recommended for your region (such as MTU-1010 or Swarna Sub1).
- Fertilization Balance: Avoid excess application of Nitrogen fertilizers. High nitrogen levels make leaf tissues succulent, increasing susceptibility to blast. Use a split dose of nitrogen (50% basal, 25% at tillering, and 25% at panicle initiation).
- Water Management: Keep fields flooded with water (2-5 cm depth) where possible. Blast spreads faster in dry, upland soil conditions.
- Fungicidal Spray: If leaf blast lesions exceed 5% leaf area, spray Tricyclazole 75 WP at 0.6 grams per litre of water, or Carbendazim at 1 gram per litre of water. Repeat spray after 10-14 days if needed.
"""

WHEAT_FERTILIZER_GUIDE = """# Government of India Department of Agriculture - Wheat Crop Guidelines
## Module 3: Fertilizer Management for High Yield

Nitrogen Dosage Recommendations for Wheat:
For irrigated, timely-sown dwarf wheat crops, the general recommended dose of Nitrogen (N) is 120 kg per hectare (kg/ha). 

Split Application Guidelines:
1. Basal Application (Sowing Time): Apply 50% of the total nitrogen (60 kg/ha) along with full doses of Phosphorus (60 kg/ha P2O5) and Potassium (40 kg/ha K2O) at the time of sowing.
2. First Top Dressing (Crown Root Initiation stage - 21 days after sowing): Apply 25% of nitrogen (30 kg/ha) immediately after the first irrigation.
3. Second Top Dressing (Tillering to Jointing stage - 40-45 days after sowing): Apply the remaining 25% of nitrogen (30 kg/ha) with the second irrigation.

For rainfed wheat crops, reduce the Nitrogen dose to 60-80 kg/ha and apply the entire quantity as a basal application during sowing, embedded deep into the soil to retain moisture.
"""

# Let's add Telugu sample document to test multilingual native retrieval!
TELUGU_TOMATO_GUIDE = """టమోటా ఆకు ముడుత తెగులు నివారణ (TYLCV)
ఆంధ్రప్రదేశ్ వ్యవసాయ విశ్వవిద్యాలయం - రైతు సలహా పత్రం

టమోటా ఆకు ముడుత వైరస్ లక్షణాలు:
ఈ తెగులు తెల్ల దోమల (వైట్ ఫ్లైస్) ద్వారా వ్యాపిస్తుంది. తెగులు సోకిన టమోటా మొక్కలు ఎదగవు, ఆకులు చిన్నవిగా మారి పైకి మరియు లోపలికి ముడుచుకుపోతాయి. ఆకుల అంచులు పసుపు రంగులోకి మారుతాయి. పూత మరియు కాయ రావడం తగ్గిపోతుంది, దీనివల్ల దిగుబడి తీవ్రంగా దెబ్బతింటుంది.

నివారణ చర్యలు:
1. తోటలో ఎకరానికి 15-20 పసుపు జిగురు బోర్డులు ఏర్పాటు చేసి తెల్లదోమల ఉధృతిని గమనించాలి.
2. తెల్లదోమ నివారణకు ఇమిడాక్లోప్రిడ్ (0.5 మి.లీ లీటరు నీటికి) లేదా వేప నూనె (10,000 PPM) 3 మి.లీ లీటరు నీటికి కలిపి పిచికారీ చేయాలి.
3. నర్సరీ దశలోనే 40-మెష్ నైలాన్ నెట్లను ఉపయోగించి మొక్కలను దోమల బారిన పడకుండా రక్షించాలి.
"""

def setup_samples():
    """Writes sample documents to data/documents/ to enable testing."""
    docs_dir = config.get_absolute_path("paths.documents_dir")
    os.makedirs(docs_dir, exist_ok=True)
    
    files = {
        "icar_tomato_guide.txt": TOMATO_GUIDE,
        "kvk_rice_blast_manual.txt": RICE_BLAST_MANUAL,
        "wheat_fertilizer_guide.md": WHEAT_FERTILIZER_GUIDE,
        "telugu_tomato_guide.txt": TELUGU_TOMATO_GUIDE
    }
    
    print(f"\nCreating sample documents in {docs_dir}...")
    for filename, content in files.items():
        filepath = os.path.join(docs_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   [+] Created {filename}")
        else:
            print(f"   [-] {filename} already exists. Skipping.")
            
    print("Done setting up sample files.\n")

if __name__ == "__main__":
    setup_samples()
