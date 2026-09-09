from pvf_parser import PVFParser
import re

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

# 所有职业的.chr文件
chr_files = {
    '0': 'character/swordman/swordman.chr',        # 鬼剑士
    '1': 'character/fighter/fighter.chr',          # 格斗家
    '2': 'character/gunner/gunner.chr',            # 神枪手
    '3': 'character/mage/mage.chr',                # 魔法师
    '4': 'character/priest/priest.chr',            # 圣职者
    '5': 'character/gunner/atgunner.chr',          # 神枪手(女)
    '6': 'character/thief/thief.chr',              # 暗夜使者
    '7': 'character/fighter/atfighter.chr',        # 格斗家(男)
    '8': 'character/mage/atmage.chr',              # 魔法师(男)
    '9': 'character/swordman/dsswordman.chr',      # 黑暗武士
    '10': 'character/mage/creatormage.chr',        # 缔造者
    '11': 'character/swordman/atswordman.chr',     # 鬼剑士(女)
    '12': 'character/knight/knight.chr',           # 守护者
    '13': 'character/demoniclancer/demoniclancer.chr', # 魔枪士
    '14': 'character/priest/atpriest.chr',         # 圣职者(女)
    '15': 'character/gunblader/gunblader.chr',     # 枪剑士
}

print()
print('=== 提取各职业觉醒技能ID ===')
print()

for job, chr_path in chr_files.items():
    try:
        text = parser.read_file_text(chr_path)
        if not text:
            print(f'job={job}: 无法读取文件')
            continue
        
        # 提取 [awakening name] 部分
        awakening_section = None
        if '[awakening name]' in text:
            # 找到 [awakening name] 之后的内容
            idx = text.index('[awakening name]')
            awakening_section = text[idx:idx+3000]
        
        # 提取一次觉醒技能ID
        awaken1_skills = []
        awaken2_skills = []
        
        # 查找 [awakening 1] 部分的 skill
        if awakening_section:
            # 分割为 awakening 1 和 awakening 2
            parts = re.split(r'\[awakening \d+\]', awakening_section)
            
            if len(parts) >= 2:
                # awakening 1 部分
                aw1_text = parts[1]
                # 查找 [skill] 部分
                skill_match = re.search(r'\[skill\]\s*(.*?)\s*\[/skill\]', aw1_text, re.DOTALL)
                if skill_match:
                    skills = skill_match.group(1).strip().split()
                    # 技能ID是奇数位置（0, 2, 4...）
                    awaken1_skills = [int(skills[i]) for i in range(0, len(skills), 2) if i < len(skills)]
            
            if len(parts) >= 3:
                # awakening 2 部分
                aw2_text = parts[2]
                skill_match = re.search(r'\[skill\]\s*(.*?)\s*\[/skill\]', aw2_text, re.DOTALL)
                if skill_match:
                    skills = skill_match.group(1).strip().split()
                    awaken2_skills = [int(skills[i]) for i in range(0, len(skills), 2) if i < len(skills)]
        
        # 如果没找到 awakening 部分，尝试从 growtype 中查找 showskill level=50 的技能
        if not awaken1_skills:
            # 查找所有 [showskill level] 后面的数字
            showskill_matches = re.findall(r'\[showskill level\]\s*(\d+)\s*\[show skill\]\s*(.*?)\s*\[/show skill\]', text, re.DOTALL)
            for level, skills_text in showskill_matches:
                if int(level) >= 50:
                    skills = skills_text.strip().split()
                    skill_ids = [int(skills[i]) for i in range(0, len(skills), 2) if i < len(skills)]
                    if not awaken1_skills:
                        awaken1_skills = skill_ids
        
        job_names = {
            '0': '鬼剑士', '1': '格斗家', '2': '神枪手', '3': '魔法师', '4': '圣职者',
            '5': '神枪手(女)', '6': '暗夜使者', '7': '格斗家(男)', '8': '魔法师(男)',
            '9': '黑暗武士', '10': '缔造者', '11': '鬼剑士(女)', '12': '守护者',
            '13': '魔枪士', '14': '圣职者(女)', '15': '枪剑士'
        }
        
        print(f'job={job} ({job_names.get(job, "?")}):')
        print(f'  一次觉醒技能: {awaken1_skills}')
        print(f'  二次觉醒技能: {awaken2_skills}')
        print()
        
    except Exception as e:
        print(f'job={job}: 读取失败 - {e}')
        print()
