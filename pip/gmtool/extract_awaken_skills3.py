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
print('=== 提取各职业觉醒技能ID（[awakening skill]标签）===')
print()

result = {}

for job, chr_path in chr_files.items():
    try:
        text = parser.read_file_text(chr_path)
        if not text:
            print(f'job={job}: 无法读取文件')
            continue
        
        # 查找所有 [awakening name] 部分
        # 每个转职都有一个 [awakening name] 部分
        awakening_sections = []
        idx = 0
        while True:
            idx = text.find('[awakening name]', idx)
            if idx == -1:
                break
            # 找到下一个 [growtype 或文件结束
            next_idx = text.find('[growtype', idx + 1)
            if next_idx == -1:
                next_idx = len(text)
            section = text[idx:next_idx]
            awakening_sections.append(section)
            idx = next_idx
        
        # 对每个转职，提取一次觉醒和二次觉醒技能
        job_awaken_skills = []
        for i, section in enumerate(awakening_sections):
            # 提取 [awakening 1] 部分
            aw1_skills = []
            aw1_match = re.search(r'\[awakening 1\](.*?)(?=\[awakening 2\]|\Z)', section, re.DOTALL)
            if aw1_match:
                aw1_text = aw1_match.group(1)
                skill_match = re.search(r'\[awakening skill\]\s*(.*?)\s*\[/awakening skill\]', aw1_text, re.DOTALL)
                if skill_match:
                    skills = skill_match.group(1).strip().split()
                    aw1_skills = [int(skills[j]) for j in range(0, len(skills), 2) if j < len(skills)]
            
            # 提取 [awakening 2] 部分
            aw2_skills = []
            aw2_match = re.search(r'\[awakening 2\](.*?)(?=\Z)', section, re.DOTALL)
            if aw2_match:
                aw2_text = aw2_match.group(1)
                skill_match = re.search(r'\[awakening skill\]\s*(.*?)\s*\[/awakening skill\]', aw2_text, re.DOTALL)
                if skill_match:
                    skills = skill_match.group(1).strip().split()
                    aw2_skills = [int(skills[j]) for j in range(0, len(skills), 2) if j < len(skills)]
            
            job_awaken_skills.append({
                'growtype': i,
                'awaken1': aw1_skills,
                'awaken2': aw2_skills
            })
        
        result[job] = job_awaken_skills
        
        print(f'job={job} ({job_names.get(job, "?")}): 共{len(awakening_sections)}个转职')
        for gs in job_awaken_skills:
            print(f'  转职{gs["growtype"]}: 一觉={gs["awaken1"]}, 二觉={gs["awaken2"]}')
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
    print(f"    '{job}': [")
    for gs in result[job]:
        print(f"        {{'growtype': {gs['growtype']}, 'awaken1': {gs['awaken1']}, 'awaken2': {gs['awaken2']}}},")
    print(f"    ],")
print('}')
