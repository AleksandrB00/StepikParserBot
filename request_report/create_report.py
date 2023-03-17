import glob

async def create_open_chat_report(all_participants, flag):
    target = '*.txt'
    file = glob.glob(target)[0] 
    with open(file, "w", encoding="utf-8") as write_file:
        for participant in all_participants:
            if flag == 'users':
                if participant.username != None and participant.bot == False and participant.fake == False:
                    write_file.writelines(f"@{participant.username}\n")
            if flag == 'phones':
                if participant.username != None and participant.bot == False and participant.fake == False and participant.phone != None:
                    write_file.writelines(f"@{participant.username} Тел. {participant.phone}\n")
    uniqlines = set(open(file,'r', encoding='utf-8').readlines())
    open(file,'w', encoding='utf-8').writelines(set(uniqlines))