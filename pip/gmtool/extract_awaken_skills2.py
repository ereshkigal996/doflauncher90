from pvf_parser import PVFParser
import re

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

# 所有职业的.chr文件
chr_files = {
    '0': 'character/swordman/swordman.chr',
    '1': 'character/fighter/fighter.chr',
    '2': 'character/gunner/gunner.chr',
    '3': 'character/mage/mage.chr',
    '4': 'character/priest/priest.chr',
    '5': 'character/gunner/atgunner.chr',
    '6': 'character/thief/thief.chr',
    '7': 'character/fighter/atfighter.chr',
    '8': 'character/mage/atmage.chr',
    '9': 'character/swordman/dsswordman.chr',
    '10': 'character/mage/creatormage.chr',
    '11': 'character/swordman/atswordman.chr',
    '12': 'character/knight/knight.chr',
    '13': 'character/demoniclancer/demoniclancer.chr',
    '14': 'character/priest/atpriest.chr',
    '15': 'character/gunblader/gunblader.chr',
}

job_names = {
    '0': '鬼剑士', '1': '格斗家', '2': '神枪手', '3': '魔法师', '4': '圣职者',
    '5': '神枪手(女)', '6': '暗夜使者', '7': '格斗家(男)', '8': '魔法师(男)',
    '9': '黑暗武士', '10': '缔造者', '11': '鬼剑士(女)', '12': '守护者',
    '13': '魔枪士', '14': '圣职者(女)', '15': '枪剑士'
}

print()
print('=== 提取各职业觉醒技能ID（根据showskill level）===')
print()

result = {}

for job, chr_path in chr_files.items():
    try:
        text = parser.read_file_text(chr_path)
        if not text:
            print(f'job={job}: 无法读取文件')
            continue
        
        # 查找所有 [showskill level] 和对应的 [show skill]
        # 模式: [showskill level]\n<level>\n[show skill]\n<skills>\n[/show skill]
        pattern = r'\[showskill level\]\s*(\d+)\s*\[show skill\]\s*(.*?)\s*\[/show skill\]'
        matches = re.findall(pattern, text, re.DOTALL)
        
        awaken1_skills = []
        awaken2_skills = []
        
        for level_str, skills_text in matches:
            level = int(level_str)
            skills = skills_text.strip().split()
            # 技能ID是奇数位置（0, 2, 4...），后面跟着的是等级要求
            skill_ids = []
            for i in range(0, len(skills), 2):
                if i < len(skills):
                    try:
                        skill_id = int(skills[i])
                        skill_ids.append(skill_id)
                    except:
                        pass
            
            if level == 50:
                awaken1_skills = skill_ids
            elif level == 75:
                awaken2_skills = skill_ids
        
        # 如果没找到50级的，尝试查找 awakening name 部分的技能
        if not awaken1_skills and '[awakening name]' in text:
            idx = text.index('[awakening name]')
            aw_text = text[idx:idx+5000]
            
            # 查找 [awakening 1] 后的 [skill]
            aw1_match = re.search(r'\[awakening 1\].*?\[skill\]\s*(.*?)\s*\[/skill\]', aw_text, re.DOTALL)
            if aw1_match:
                skills = aw1_match.group(1).strip().split()
                awaken1_skills = [int(skills[i]) for i in range(0, len(skills), 2) if i < len(skills)]
            
            aw2_match = re.search(r'\[awakening 2\].*?\[skill\]\s*(.*?)\s*\[/skill\]', aw_text, re.DOTALL)
            if aw2_match:
                skills = aw2_match.group(1).strip().split()
                awaken2_skills = [int(skills[i]) for i in range(0, len(skills), 2) if i < len(skills)]
        
        result[job] = {
            'awaken1': awaken1_skills,
            'awaken2': awaken2_skills
        }
        
        print(f'job={job} ({job_names.get(job, "?")}):')
        print(f'  一次觉醒技能(50级): {awaken1_skills}')
        print(f'  二次觉醒技能(75级): {awaken2_skills}')
        print()
        
    except Exception as e:
        print(f'job={job}: 读取失败 - {e}')
        import traceback
        traceback.print_exc()
        print()

# 输出结果为Python字典格式
print()
print('=== 结果（Python字典格式）===')
print('AWAKEN_SKILLS = {')
for job in sorted(result.keys(), key=lambda x: int(x)):
    print(f"    '{job}': {{'awaken1': {result[job]['awaken1']}, 'awaken2': {result[job]['awaken2']}}},")
print('}')
