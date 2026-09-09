import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from pvf_parser import PVFParser

parser = PVFParser(r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf')
parser.load()

archive_path = 'equipment/character/partset2/set_item_31128.equ'
text = parser.read_file_text(archive_path)
if text:
    print(f'=== {archive_path} ===')
    print(text)
