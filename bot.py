import datetime
import os
import sqlite3
import itertools
from discord.ext import tasks, commands
from multielo import MultiElo
from pathlib import Path

bot = commands.Bot(command_prefix='!')
bd_match = 'match'
bd_user = 'users'
bd_log = 'log'
elo = MultiElo()
dbg_info_in_channel = 'no'
dbg_info_in_console = 'yes'
days_create_match = 1
start_elo = 100
id_channel = '912553521629495336'  # impulse_test channel 916723980113682452 #dbg 912553521629495336

fle = Path('botkey.txt')
fle.touch(exist_ok=True)
bot_key_api_file = open(fle)




def bd_backup(status=''):
    def progress(status, remaining, total):
        print(f'Copied {total - remaining} of {total} pages...')

    now = datetime.datetime.now()
    bkp_name = 'backup_' + str(status) + ' ' + str(now.year) + '.' + str(now.month) + '.' + str(now.day) + ' ' + str(now.hour) + '_' + str(now.minute) + '_' + str(now.second) + '.db'
    con = sqlite3.connect('bd.db')
    bck = sqlite3.connect(bkp_name)
    with bck:
        con.backup(bck, pages=1, progress=progress)
    bck.close()
    con.close()
    os.makedirs("DB_backup/", exist_ok=True)
    os.replace(bkp_name, "DB_backup/" + bkp_name)
    print(f'bkp_ok')


class bot_loop(commands.Cog):
    def __init__(self):
        self.index = 0
        self.bmain.start()

    def cog_unload(self):
        self.bmain.cancel()


    @tasks.loop(hours=12.0)
    async def bkp(self):
        print(f'DBG_ 🚩 [!!!!] Прошло 12 часов')
        # bd_backup()

    @tasks.loop(minutes=1.0)  # выполняется каждую минуту
    async def bmain(self):
        channel = await bot.fetch_channel(id_channel)
        now = datetime.datetime.now()
        endmatchtime2 = now + datetime.timedelta(days=days_create_match)
        endmatchtime = endmatchtime2.replace(hour=0, minute=0, second=0, microsecond=0)

        lastgame_create_time_sql = cur.execute('SELECT MAX(date_end) FROM weekend').fetchone()  # запрос из бд по самой последней дате в колонке date_end
        lastgame_create = datetime.datetime.strptime(lastgame_create_time_sql[0], "%Y-%m-%d %H:%M:%S")
        # print('now ----  lastgame_time '+str(now.day)+'.'+str(now.month)+'.'+str(now.year)+'  ----  '+str(lastgame_time.day)+'.'+str(lastgame_time.month)+'.'+str(lastgame_time.year))
        chk_ok = cur.execute('SELECT id FROM match where match_end=0 and check_1=1 and check_2=1 and check_ok=0')
        a = []  # лист ID матчей
        for user in chk_ok: a.append(str(user[0]))  # создать список матчей с подтврежденными играми
        for i in a:  # отметить check_ok если оба потвердили

            cur.execute(f'UPDATE match SET check_ok = 1 WHERE id = {i}')
            base.commit()

        if now >= lastgame_create:
            cur.execute('UPDATE match SET match_end = 1 WHERE check_ok=0 and match_end = 0').fetchone() # отметить все матчи завершеными.
            base.commit()
            await channel.send('Время вышло. Все матчи завершены')

            pari = create_new_matchs()  # создать новые матчи
            for user_id in pari[0]:
                message = await channel.send(f'<@{user_id[0]}> vs <@{user_id[1]}>')  # отправляем сообщения и получаем ИД о матче
                if dbg_info_in_console == 'yes': log_in_db('admin',
                                                           f'[MSG] создан матч  {str(message.id)}. '
                                                           f'{return_name_on_id(user_id[0])} против '
                                                           f'{return_name_on_id(user_id[1])}')
                cur.execute(f'INSERT INTO {bd_match} (id,user_1,user_2) '
                            f'VALUES("{message.id}", "{user_id[0]}", "{user_id[1]}")')
                base.commit()
            pari[1] = str(pari[1])
            await channel.send(f'<@{str(pari[1][2:-2])}> остался без соперника')  # один остался без пары
            # создать запись о датах начала и конца недели
            cur.execute(f'INSERT INTO weekend (date_start,date_end,player_play,player_not_play) VALUES '
                        f'("{str(now)}","{str(endmatchtime)}",0,0)')
            base.commit()
            bd_backup()

# def hello_world(): # для создания второго потока и отсчета времени. работает но закрыть бот нужно через диспетчер задач
#  while True:
#     print("Hello, World!")
#     time.sleep(6)
# t1 = threading.Thread(target=hello_world)
# t1.start()

@bot.command(brief='Регистрация нового пользователя',
             description='Через пробел можно указать дополнительно информацию о себе')
async def reg(ctx, info=None):
    name_server = ctx.guild.name
    user_id = ctx.author.id
    now = datetime.datetime.now()

    registred = cur.execute('SELECT * FROM {} WHERE user_id == ?'.format(bd_user), (user_id,)).fetchone()
    if registred == None:
        cur.execute(f'INSERT INTO {bd_user} (user_id,name,info,server,elo,date_reg) VALUES("'
                    f'{user_id}", "{ctx.author.name}", "{info}", "{name_server}", "{start_elo}", {now})').fetchone()
        base.commit()
         #TODO: добавить защиту от Sql-иньекций
        await ctx.send('зареган ' + ctx.author.name)
        log_in_db(user_id, f' Registred user {str(return_name_on_id(user_id))}', name_server)
    else:
        await ctx.send('уже есть пользователь ' + ctx.author.name)

@bot.event
async def on_raw_reaction_add(payload):  # чекает новые реакции

    id_mess = payload.message_id
    user_id = payload.user_id
    check_emoji = payload.emoji

    if dbg_info_in_channel == 'yes':
        channel = await bot.fetch_channel('912553521629495336')  # dbg канал
    else:
        channel = await bot.fetch_channel(payload.channel_id)  # канал где к боту обратились
    #  if dbg_info_in_channel == 'yes':print(type(payload.channel_id))

    channel_mes = bot.get_channel(payload.channel_id)
    message = await channel_mes.fetch_message(payload.message_id)
    user = bot.get_user(payload.user_id)
    if not user:
        user = await bot.fetch_user(payload.user_id)
    id_match = cur.execute(f'SELECT * FROM {bd_match} WHERE id == "{id_mess}"').fetchone()

    if not id_match == None and str(check_emoji) == '👍' and not str(id_match[7]) == '1':  # чекает реакции на сообщения о матче 1х1 проверяя по ИД сообщения и в базе по ИД матча.

        # ставит пометку в базу о готовности
        if int(id_match[1]) == user_id and str(check_emoji) == '👍':
            await channel.send(f'<@{str(user_id)}> подвтердил')
            cur.execute(f'Update {bd_match} set check_1 = 1 WHERE id == "{id_mess}"').fetchone()
            base.commit()

        if int(id_match[2]) == user_id and str(check_emoji) == '👍':
            await channel.send(f'<@{str(user_id)}> подвтердил')
            cur.execute(f'Update {bd_match} set check_2 = 1 WHERE id == "{id_mess}"').fetchone()
            base.commit()

    if str(check_emoji) == '✅' and not id_match == None and not str(
            id_match[7]) == '1':  # #тут код для реакции о победе или проигрыше ✅ 🚫
        if int(id_match[1]) == user_id:  # первый игрок ✅
            await channel.send(f'<@{str(user_id)}> отчитался о победе')
            # print('DBG_ 🚩: ' + str(payload.emoji))
            if str(id_match[6]) == 'win':  # win2 win
                await channel.send('Второй уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
            elif str(id_match[5]) == 'los':  # win1 los
                await channel.send(f'<@{str(user_id)}> ты уже отчитался о проигрыше')
                # await payload.reaction.remove()
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[6]) == 'los':  # win2 los
                    name2 = cur.execute('SELECT user_2 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send(f'<@{str(user_id)}> победил <@{str(name2[0])}>')
                    cur.execute(f'Update {bd_match} set win1 = win, match_end = 1  WHERE id == "{id_mess}"').fetchone()
                    cur.execute(f'Update {bd_user} set win = win + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()
                    await message.add_reaction('🤝')  # 🤝 поставить реакцию на матч
                    end_match_elo(str(user_id), str(name2[0]), id_mess)
                else:
                    cur.execute(f'Update {bd_match} set win1 = win  WHERE id == "{id_mess}"').fetchone()
                    cur.execute(f'Update {bd_user} set win = win + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()

        if int(id_match[2]) == user_id:  # второй игрок ✅
            await channel.send(f'<@{str(user_id)}> отчитался о победе')
            if str(id_match[5]) == 'win':
                await channel.send('Первый уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
            elif str(id_match[6]) == 'los':
                await channel.send(f'<@{str(user_id)}> ты уже отчитался о проигрыше')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[5]) == 'los':
                    name1 = cur.execute(f'SELECT user_1 FROM {bd_match} WHERE id == "{id_mess}"').fetchone()
                    await channel.send(f'<@{str(user_id)}> победил <@{str(name1[0])}>')
                    cur.execute(f'Update {bd_match} set win2 = win, match_end = 1  WHERE id == "{id_mess}"').fetchone()
                    base.commit()
                    cur.execute(f'Update {bd_user} set win = win + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()
                    end_match_elo(str(user_id), str(name1[0]), id_mess)
                    await message.add_reaction('🤝')
                else:
                    cur.execute(f'Update {bd_match} set win2 = win  WHERE id == "{id_mess}"').fetchone()
                    base.commit()
                    cur.execute(f'Update {bd_user} set win = win + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()


    if str(check_emoji) == '🚫' and not id_match == None and not str(id_match[7]) == '1':  #
        if int(id_match[1]) == user_id:  # первый игрок 🚫
            await channel.send(f'<@{str(user_id)}> отчитался о проигрыше')
            if str(id_match[6]) == 'los':
                await channel.send(f'<@{str(user_id)}> уже отчитался о проигрыше')
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            elif str(id_match[5]) == 'win':
                await channel.send(f'<@{str(user_id)}> ты уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[6]) == 'win':
                    name2 = cur.execute('SELECT user_2 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send(f'<@{str(user_id)}> проиграл <@{str(name2[0])}>')
                    cur.execute(f'Update {bd_match} set win1 = los, match_end = 1 WHERE id == "{id_mess}"').fetchone()
                    cur.execute(f'Update {bd_user} set los = los + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()
                    end_match_elo(str(name2[0]), str(user_id), id_mess)
                    await message.add_reaction('🤝')
                    if dbg_info_in_console == 'yes':
                        log_in_db(payload.author.id, f'[DBG] 🚩 {str(name2[0])} 🚫 {str(user_id)}', payload.guild.name)
                else:
                    cur.execute(f'Update {bd_match} set win1 = los WHERE id == "{id_mess}"').fetchone()
                    cur.execute(f'Update {bd_user} set los = los + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()

        if int(id_match[2]) == user_id:  # второй игрок 🚫
            await channel.send(f'<@{str(user_id)}> отчитался о проигрыше')
            if str(id_match[5]) == 'los':
                await channel.send(f'<@{str(user_id)}> уже отчитался о проигрыше')
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            elif str(id_match[6]) == 'win':
                await channel.send(f'<@{str(user_id)}> ты уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[5]) == 'win':
                    name1 = cur.execute('SELECT user_1 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send(f'<@{str(user_id)}> проиграл <@{str(name1[0])}>')
                    cur.execute(f'Update {bd_match} set win2 = los, match_end = 1 WHERE id == "{id_mess}"').fetchone()
                    cur.execute(f'Update {bd_user} set los = los + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()
                    end_match_elo(str(name1[0]), str(user_id), id_mess)
                    await message.add_reaction('🤝')
                else:
                    cur.execute(f'Update {bd_match} set win2 = los WHERE id == "{id_mess}"').fetchone()
                    cur.execute(f'Update {bd_user} set los = los + 1 WHERE user_id = "{str(user_id)}"').fetchone()
                    base.commit()

def create_new_matchs():
    global non_in_game_id
    user_list = []  # Список игроков ID
    user_elo_id = {}  # рейтинг игроков c ID
    name = {}
    users = cur.execute('SELECT user_id,elo,name FROM {} '.format(bd_user), )

    for user in users:
        user_list.append(str(user[0]))
        user_elo_id[str(user[0])] = user[1]
        name[str(user[0])] = user[2]

    raunds = {i: abs(user_elo_id[i[0]] - user_elo_id[i[1]]) for i in itertools.combinations(user_list, 2)} #Все комбинации для игры с разницей рейтинга
    sorted_tuple = sorted(raunds.items(), key=lambda x: x[1]) #Отсортированно по разнице рейтинга
    user_filter = []
    pari = []
    pari_n = []
    for i in sorted_tuple:

        if (i[0][0] not in user_filter) and (i[0][1] not in user_filter):
            user_filter.append(i[0][0])
            user_filter.append(i[0][1])
            pari_n.append((name[i[0][0]], name[i[0][1]]))
            pari.append((i[0][0], i[0][1]))

    if dbg_info_in_console == 'yes':
        print(f' Пары для игры \n{pari_n}')
        print(f' Этот ID не играет сегодня {set(user_list) - set(user_filter)}, его имя {name[list(set(user_list) - set(user_filter))[0]]}')
        non_in_game_id = set(user_list) - set(user_filter)
    return [pari,non_in_game_id]

@bot.command(brief='Тестовая команда для создания матчей')
async def t2(ctx):
    pari = create_new_matchs()
    if dbg_info_in_console == 'yes': log_in_db(ctx.author.id, f'[DBG] pari = {str(pari[1])} type {type(pari)}', ctx.guild.name)
    for i in pari[0]:
        if dbg_info_in_console == 'yes': log_in_db(ctx.author.id, f'[MSG] {i[0]} против {i[1]}', ctx.guild.name)
        message = await ctx.send('<@' + i[0] + '> vs <@' + i[1] + '>')  # отправляем и получаем ИД сообщения о матче
        if dbg_info_in_console == 'yes': log_in_db(ctx.author.id, f'[DBG] создан матч {str(message.id)}', ctx.guild.name)
        cur.execute('INSERT INTO {} (id,user_1,user_2) VALUES(?, ?, ?)'.format(bd_match),(message.id, i[0], i[1])).fetchone()
        base.commit()
    pari[1] = str(pari[1])
    await ctx.send('<@' + str(pari[1][2:-2]) + '> остался без соперника')  # один остался без пары

@bot.command(brief='Create challenge', description='Через пробел указать противника')
async def vs(ctx, arg=None):
    log_in_db(ctx.author.id, f'[INFO] !VS arg = {str(arg)}', ctx.guild.name)
    if arg == None: return
    # name_server = ctx.guild.name
    user1_id = ctx.author.id
    now = datetime.datetime.now()
    user2_id = (str(arg[3:-1]))
    user2_chk = cur.execute('SELECT user_id FROM {} WHERE user_id == ?'.format(bd_user), (user2_id,)).fetchone()
    if user2_chk == None or str(user1_id) == user2_id: return
    challenge = return_name_on_id(user1_id)
    if dbg_info_in_console == 'yes': log_in_db(ctx.author.id, f'msg {return_name_on_id(user1_id)} против {return_name_on_id(user2_id)}', ctx.guild.name)
    message = await ctx.send('<@' + str(user1_id) + '> vs <@' + str(user2_id) + '>')  # отправляем и получаем ИД сообщения о матче
    if dbg_info_in_console == 'yes': log_in_db(ctx.author.id, f'[INFO] VS создан матч {str(message.id)}', ctx.guild.name)
    cur.execute('INSERT INTO {} (id,user_1,user_2,challenge) VALUES(?, ?, ?, ?)'.format(bd_match),(message.id, str(user1_id), user2_id, challenge)).fetchone()
    base.commit()
    log_in_db(ctx.author.id, f'[INFO] VS message.id={message.id} user1_id={user1_id} user2_id={user2_id}', ctx.guild.name)

@bot.command(brief='Admin tools', description='Через пробел указать админа')
async def adminreg(ctx, arg=None):
    if arg == None: return
    name_server = ctx.guild.name
    user_id = ctx.author.id
    user_add = (str(arg[3:-1]))
    admin_chk = cur.execute('SELECT user_id FROM {} WHERE adm == 1 AND user_id == ?'.format(bd_user), (user_id,)).fetchone()
    if admin_chk == None or str(user_id) == user_add: return
    if user_id == admin_chk[0]:
        cur.execute('Update {} set adm = 1  WHERE user_id == ?'.format(bd_user),(str(user_add),)).fetchone()
        base.commit()
        log_in_db(user_id, f'[ADM] add admin {str(return_name_on_id(user_add))}', name_server)

@bot.command(brief='Admin tools', description='Через пробел указать админа')
async def admindel(ctx, arg=None):
    if arg == None: return
    name_server = ctx.guild.name
    user_id = ctx.author.id
    user_add = (str(arg[3:-1]))
    admin_chk = cur.execute('SELECT user_id FROM {} WHERE adm == 1 AND user_id == ?'.format(bd_user), (user_id,)).fetchone()
    if admin_chk == None or str(user_id) == user_add: return
    if user_id == admin_chk[0]:
        cur.execute('Update {} set adm = 0  WHERE user_id == ?'.format(bd_user), (str(user_add),)).fetchone()
        base.commit()
        print(f'DBG_ [ADMIN] !admindel now admin = {str(return_name_on_id(user_add))}')
        log_in_db(user_id, f'[ADM] del admin {str(return_name_on_id(user_add))}', name_server)

def log_in_db(user_id='admin',command=None,server=None):
    time_now = datetime.datetime.now()
    user_id = user_id.replace('_', '') #небольшая защита от иньекций из имени пользователя
    if type(user_id) == int:
        user_name = str(return_name_on_id(user_id))
    else:
        user_name = str(user_id)
    cur.execute(f'INSERT INTO {bd_log} (user,command,date,server) VALUES("{user_name}", "{str(command)}", "{str(time_now)}", "{str(server)}")')
    base.commit()

def return_name_on_id(user_id):
    return (str(cur.execute('SELECT name FROM {} WHERE user_id == ?'.format(bd_user), (user_id,)).fetchone())[2:-3])

def end_match_elo(win_user_id, los_user_id, id_mess):
    name_users = cur.execute('SELECT user_1,user_2 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
    user1 = cur.execute('SELECT * FROM {} WHERE user_id == ?'.format(bd_user), (str(name_users[0]),)).fetchone()
    user2 = cur.execute('SELECT * FROM {} WHERE user_id == ?'.format(bd_user), (str(name_users[1]),)).fetchone()

    if user1[6] == None or user2[6] == None:
        log_in_db('admin', f'[ERROR]  ELO None:  user1= {str(user1[6])} user2= {str(user2[6])}')
        return
    if dbg_info_in_console == 'yes':
        log_in_db('admin', f'[DBG] 🚩 fnk elo == {str(win_user_id)} los = {str(los_user_id)}')
    if win_user_id == name_users[0]:  # если победитель_id равен юзеру1
        if dbg_info_in_console == 'yes':
            log_in_db('admin', f'[DBG] 🚩 1 win_user_id == {str(name_users[0])}')
        result = elo.get_new_ratings([int(user1[6]), int(user2[6])])
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[0]), str(user1[0]),)).fetchone()
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[1]), str(user2[0]),)).fetchone()
        base.commit()
    if win_user_id == name_users[1]:  # если победитель_id равен юзеру2
        if dbg_info_in_console == 'yes':
            log_in_db('admin', f'[DBG] 🚩 2 win_user_id == {str(name_users[1])}')
        result = elo.get_new_ratings([int(user2[6]), int(user1[6])])
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[0]), str(user1[0]),)).fetchone()
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[1]), str(user2[0]),)).fetchone()
        base.commit()
    log_in_db('admin', f'[DBG] 🚩 new ELO:  {return_name_on_id(user1[0])}={(str(result[0]))} : {return_name_on_id(user2[0])}={(str(result[1]))}')

@bot.event
async def on_raw_reaction_remove(payload):  # чекает реакции на удаление
    id_mess = payload.message_id
    user_id = payload.user_id
    check_emoji = payload.emoji

    if dbg_info_in_channel == 'yes':
        channel = await bot.fetch_channel('912553521629495336')  # dbg канал
    else:
        channel = await bot.fetch_channel(payload.channel_id)  # канал где к боту обратились

    # channel = await bot.fetch_channel(payload.channel_id)
    id_match = cur.execute('SELECT * FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()

    if not id_match == None and str(check_emoji) == '👍' and not str(id_match[7]) == '1':  # отмена готовности
        if int(id_match[1]) == user_id:
            await channel.send(f'<@{str(user_id)}> отменил готовность')
            cur.execute('Update {} set check_1 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()
        if int(id_match[2]) == user_id:
            await channel.send(f'<@{str(user_id)}> отменил готовность')
            cur.execute('Update {} set check_2 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()

    if not id_match == None and str(check_emoji) == '✅' and not str(id_match[7]) == '1':  # отмена победы
        if int(id_match[1]) == user_id:
            await channel.send(f'<@{str(user_id)}> отменил победу')
            cur.execute('Update {} set win1 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()
        if int(id_match[2]) == user_id:
            await channel.send(f'<@{str(user_id)}> отменил победу')
            cur.execute('Update {} set win2 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()

    if not id_match == None and str(check_emoji) == '🚫' and not str(id_match[7]) == '1':  # отмена проигрыша
        if int(id_match[1]) == user_id:
            await channel.send(f'<@{str(user_id)}> отменил проигрыш')
            cur.execute('Update {} set win1 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()
        if int(id_match[2]) == user_id:
            await channel.send(f'<@{str(user_id)}> отменил проигрыш')
            cur.execute('Update {} set win2 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()

@bot.command(pass_context=True, brief='Тестовая команда')
async def tst_list(ctx):
    a = []
    users = cur.execute('SELECT user_id,elo,name FROM {} '.format(bd_user), )

    for user in users:
        a.append(str(user[2]) + ' ' + str(user[1]) + '')
    await ctx.send(a)

if __name__ == '__main__':
    @bot.event
    async def on_ready():
        print('Старт бота')
        bd_backup('start')
        global base, cur
        base = sqlite3.connect('bd.db')
        cur = base.cursor()
        if base:
            print('conn db.. Ok')
        bot_loop()

    bot.run(bot_key_api_file.read())
