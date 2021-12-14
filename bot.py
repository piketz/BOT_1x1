import datetime, os, sqlite3, itertools
from discord.ext import tasks, commands
# from discord.utils import get
from multielo import MultiElo
# import numpy as np
# import threading
# import sched, discord, time, string, json

bot = commands.Bot(command_prefix='!')
bd_match = 'match'
bd_user = 'users'
elo = MultiElo()
dbg_info_in_channel = 'no'
dbg_info_in_console = 'yes'
days_create_match = 1
start_elo = 100


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


def bd_backup(status=None):
    def progress(status, remaining, total):
        print(f'Copied {total - remaining} of {total} pages...')

    now = datetime.datetime.now()
    if status == None: status = '';
    bkp_name = 'backup_' + str(status) + ' ' + str(now.year) + '.' + str(now.month) + '.' + str(now.day) + ' ' + str(now.hour) + '_' + str(now.minute) + '_' + str(now.second) + '.db'
    con = sqlite3.connect('bd.db')
    bck = sqlite3.connect(bkp_name)
    with bck:
        con.backup(bck, pages=1, progress=progress)
    bck.close()
    con.close()
    os.replace(bkp_name, "DB_backup/" + bkp_name)
    print(f'bkp_ok')


class bot_loop(commands.Cog):
    def __init__(self):
        self.index = 0
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    #####
    @tasks.loop(hours=12.0)
    async def bkp(self):
        print(f'DBG_ 🚩 [!!!!] Прошло 12 часов')
        # bd_backup()

    ####
    @tasks.loop(minutes=1.0)  # выполняется каждую минуту
    async def printer(self):
        now = datetime.datetime.now()
        endmatchtime2 = now + datetime.timedelta(days=days_create_match)
        endmatchtime = endmatchtime2.replace(hour=0, minute=0, second=0, microsecond=0)

        lastgame_time_sql = cur.execute('SELECT MAX(date_end) FROM weekend').fetchone()  # запрос из бд по самой последней дате в колонке date_end
        lastgame_time = datetime.datetime.strptime(lastgame_time_sql[0], "%Y-%m-%d %H:%M:%S")
                                                                        # 2021-12-01 00:00:00.0000  %Y-%m-%d %H:%M:%S.%f
        # next7days = lastgame_time + datetime.timedelta(days=days_create_match) #Добавить N дней к ней
        channel_dbg = await bot.fetch_channel('916723980113682452')  # impulse_test channel 916723980113682452 #dbg 912553521629495336

        # print('now ----  lastgame_time '+str(now.day)+'.'+str(now.month)+'.'+str(now.year)+'  ----  '+str(lastgame_time.day)+'.'+str(lastgame_time.month)+'.'+str(lastgame_time.year))
        #  print('endmatchtime = '+str(endmatchtime))
        chk_ok = cur.execute('SELECT id FROM match where match_end=0 and check_1=1 and check_2=1 and check_ok=0')
        a = []  # лист ID матчей
        for user in chk_ok: a.append(str(user[0]))  # создать список матчей с подтврежденными играми
        for i in a:  # отметить check_ok если оба потвердили
            # print(f'DBG_ 🚩 [INFO] i = {i} type = {type(i)}')
            cur.execute(f'UPDATE match SET check_ok = 1 WHERE id = {i}')
            base.commit()
        lastgame_time_int = lastgame_time - datetime.timedelta(hours=12)

        # print(f'DBG_ 🚩 [INFO] list a= {a}')
        # print(type(chk_ok))

        # print(f'DBG_ 🚩 [INFO] lastgame_time :  = {lastgame_time} lastgame_time-12 = {lastgame_time_int}')

        # if now >= lastgame_time_int:# and chk_ok[1] == '0':
        # print(f'DBG_ 🚩 [INFO] осталось 12 часов до конца. : lastgame_time-12 = {lastgame_time_int}')
        # await channel_dbg.send('Не подтвержденные матчи переназначаются')
        # print(f'DBG_ 🚩 [INFO] список матчей которые не подтверждены= {a}')

        if now >= lastgame_time:
            print('now >= lastgame_time  ok ' + str(now.day) + '.' + str(now.month) + '.' + str(now.year) + ' > ' + str(lastgame_time.day) + '.' + str(lastgame_time.month) + '.' + str(lastgame_time.year))
            chk2_ok = cur.execute('SELECT id FROM match where check_ok=1 ')

            # отметить все матчи завершеными.
            cur.execute('UPDATE match SET match_end = 1 WHERE check_ok=0 and match_end = 0'.format(bd_match)).fetchone()
            base.commit()

            await channel_dbg.send('Время вышло. Все матчи завершены')
            bd_backup()
            # создать новые матчи
            pari = create_new_matchs()
            for i in pari[0]:
                if dbg_info_in_console == 'yes': print(f'msg {i[0]} против {i[1]}')
                message = await channel_dbg.send('<@' + i[0] + '> vs <@' + i[1] + '>')  # отправляем и получаем ИД сообщения о матче
                if dbg_info_in_console == 'yes': print('DBG_ создан матч ' + str(message.id))
                # cur.execute('INSERT INTO {} VALUES(?, ?, ?, ?, ?, ?, ?, ?)'.format(bd_match),(message.id,i[0],i[1],0,0,0,0,0)).fetchone()
                cur.execute('INSERT INTO {} (id,user_1,user_2) VALUES(?, ?, ?)'.format(bd_match),(message.id, i[0], i[1])).fetchone()
                base.commit()
            pari[1] = str(pari[1])
            await channel_dbg.send('<@' + str(pari[1][2:-2]) + '> остался без соперника')  # один остался без пары
            # создать запись о датах начала и конца недели
            cur.execute('INSERT INTO weekend (date_start,date_end,player_play,player_not_play) VALUES (?,?,?,?)',(str(now), str(endmatchtime), 0, 0)).fetchone()
            base.commit()
            bd_backup()


# def hello_world(): # для создания второго потока и отсчета времени. работает но закрыть бот можно только через диспетчер задач
#  while True:
#     print("Hello, World!")
#     time.sleep(6)
# t1 = threading.Thread(target=hello_world)
# t1.start()


@bot.command(brief='Регистрация нового пользователя',
             description='Через пробел можно указать дополнительно информацию о себе')
async def reg(ctx, info=None):  # регистрация игрока можно указать через пробел инфу
    # info = arg
    name_server = ctx.guild.name
    user_id = ctx.author.id
    now = datetime.datetime.now()

    if ctx.author.id == '<@!406602036671676422>':  # <@!3653003926 50604544>
        await ctx.send('слава украине!')

    registred = cur.execute('SELECT * FROM {} WHERE user_id == ?'.format(bd_user), (user_id,)).fetchone()
    if registred == None:
        # cur.execute('INSERT INTO {} VALUES(?, ?, ?, ?, ?, ?, ?)'.format(bd_user),(user_id,ctx.author.name,info,name_server,0,0,100)).fetchone()
        cur.execute('INSERT  INTO {}(user_id,name,info,server,elo,date_reg) VALUES(?, ?, ?, ?, ?, ?, ?)'.format(bd_user),(user_id, ctx.author.name, info, name_server, start_elo, now)).fetchone()
        base.commit()
        await ctx.send('зареган ' + ctx.author.name)
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

    # print('DBG_ 🚩: ' + str(payload.emoji))

    id_match = cur.execute('SELECT * FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()

    #  id           user1       user2       check_1     check_2     win1        win2        match_end
    #  id_match[0]  id_match[1] id_match[2] id_match[3] id_match[4] id_match[5] id_match[6] id_match[7]

    if not id_match == None and str(check_emoji) == '👍' and not str(id_match[7]) == '1':  # чекает реакции на сообщения о матче 1х1 проверяя по ИД сообщения и в базе по ИД матча.

        # ставит пометку в базу о готовности
        if int(id_match[1]) == user_id and str(check_emoji) == '👍':
            await channel.send('<@' + str(user_id) + '> подвтердил')
            cur.execute('Update {} set check_1 = ? WHERE id == ?'.format(bd_match), ('1', id_mess,)).fetchone()
            base.commit()

        if int(id_match[2]) == user_id and str(check_emoji) == '👍':
            await channel.send('<@' + str(user_id) + '> подвтердил')
            cur.execute('Update {} set check_2 = ? WHERE id == ?'.format(bd_match), ('1', id_mess,)).fetchone()
            base.commit()

    if str(check_emoji) == '✅' and not id_match == None and not str(
            id_match[7]) == '1':  # #тут код для реакции о победе или проигрыше ✅ 🚫
        if int(id_match[1]) == user_id:  # первый игрок ✅
            await channel.send('<@' + str(user_id) + '> отчитался о победе')
            # print('DBG_ 🚩: ' + str(payload.emoji))
            if str(id_match[6]) == 'win':  # win2 win
                await channel.send('Второй уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
            elif str(id_match[5]) == 'los':  # win1 los
                await channel.send('<@' + str(user_id) + '> ты уже отчитался о проигрыше')
                # await payload.reaction.remove()
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[6]) == 'los':  # win2 los
                    name2 = cur.execute('SELECT user_2 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send('<@' + str(user_id) + '> победил <@' + str(name2[0]) + '>')
                    cur.execute('Update {} set win1 = ?, match_end = ?  WHERE id == ?'.format(bd_match),('win', '1', id_mess,)).fetchone()
                    cur.execute('Update {} set win = win + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()
                    await message.add_reaction('🤝')  # 🤝 поставить реакцию на матч
                    end_match_elo(str(user_id), str(name2[0]), id_mess)
                    if dbg_info_in_console == 'yes': print('DBG_ 🚩 первый ✅ второй  ')
                else:
                    cur.execute('Update {} set win1 = ?  WHERE id == ?'.format(bd_match), ('win', id_mess,)).fetchone()
                    cur.execute('Update {} set win = win + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()

        if int(id_match[2]) == user_id:  # второй игрок ✅
            await channel.send('<@' + str(user_id) + '> отчитался о победе')
            if str(id_match[5]) == 'win':
                await channel.send('Первый уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
            elif str(id_match[6]) == 'los':
                await channel.send('<@' + str(user_id) + '> ты уже отчитался о проигрыше')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[5]) == 'los':
                    name1 = cur.execute('SELECT user_1 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send('<@' + str(user_id) + '> победил <@' + str(name1[0]) + '>')
                    cur.execute('Update {} set win2 = ?, match_end = ?  WHERE id == ?'.format(bd_match),('win', '1', id_mess,)).fetchone()
                    base.commit()
                    cur.execute('Update {} set win = win + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()
                    end_match_elo(str(user_id), str(name1[0]), id_mess)
                    await message.add_reaction('🤝')
                    if dbg_info_in_console == 'yes': print('DBG_ 🚩 первый  второй ✅ ')
                else:
                    cur.execute('Update {} set win2 = ?  WHERE id == ?'.format(bd_match), ('win', id_mess,)).fetchone()
                    base.commit()
                    cur.execute('Update {} set win = win + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()

        # print('DBG_ chk  ' + str(check_emoji))
        # Здесь код расчета ММР/ЕЛО
        #  id           user1       user2       check_1     check_2     win1        win2        match_end
        #  id_match[0]  id_match[1] id_match[2] id_match[3] id_match[4] id_match[5] id_match[6] id_match[7]

    if str(check_emoji) == '🚫' and not id_match == None and not str(id_match[7]) == '1':  #
        if int(id_match[1]) == user_id:  # первый игрок 🚫
            await channel.send('<@' + str(user_id) + '> отчитался о проигрыше')
            if str(id_match[6]) == 'los':
                await channel.send('<@' + str(user_id) + '> уже отчитался о проигрыше')
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            elif str(id_match[5]) == 'win':
                await channel.send('<@' + str(user_id) + '> ты уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[6]) == 'win':
                    name2 = cur.execute('SELECT user_2 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send('<@' + str(user_id) + '> проиграл <@' + str(name2[0]) + '>')
                    cur.execute('Update {} set win1 = ?, match_end = ? WHERE id == ?'.format(bd_match),('los', '1', id_mess,)).fetchone()
                    cur.execute('Update {} set los = los + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()
                    end_match_elo(str(name2[0]), str(user_id), id_mess)
                    await message.add_reaction('🤝')
                    if dbg_info_in_console == 'yes': print('DBG_ 🚩 первый 🚫 второй  ')
                    if dbg_info_in_console == 'yes': print(str(name2[0]), str(user_id))
                else:
                    cur.execute('Update {} set win1 = ? WHERE id == ?'.format(bd_match), ('los', id_mess,)).fetchone()
                    cur.execute('Update {} set los = los + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()

        if int(id_match[2]) == user_id:  # второй игрок 🚫
            await channel.send('<@' + str(user_id) + '> отчитался о проигрыше')
            if str(id_match[5]) == 'los':
                await channel.send('<@' + str(user_id) + '> уже отчитался о проигрыше')
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            elif str(id_match[6]) == 'win':
                await channel.send('<@' + str(user_id) + '> ты уже отчитался о победе')
                await message.remove_reaction('✅', user)  # удалить отметку о выйгрыше
                await message.remove_reaction('🚫', user)  # удалить отметку о проигрыше
            else:
                if str(id_match[5]) == 'win':
                    name1 = cur.execute('SELECT user_1 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
                    await channel.send('<@' + str(user_id) + '> проиграл <@' + str(name1[0]) + '>')
                    cur.execute('Update {} set win2 = ?, match_end = ? WHERE id == ?'.format(bd_match),('los', '1', id_mess,)).fetchone()
                    cur.execute('Update {} set los = los + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()
                    end_match_elo(str(name1[0]), str(user_id), id_mess)
                    if dbg_info_in_console == 'yes': print('DBG_ 🚩 первый второй 🚫 ')
                    await message.add_reaction('🤝')
                else:
                    cur.execute('Update {} set win2 = ? WHERE id == ?'.format(bd_match), ('los', id_mess,)).fetchone()
                    cur.execute('Update {} set los = los + ? WHERE user_id = ?'.format(bd_user),('1', str(user_id))).fetchone()
                    base.commit()

    # завершить матч если оба поставили ✅ и 🚫


def create_new_matchs():
    a = []  # лист          Список игроков ID
    s = {}  # словарь       рейтинг игроков c ID
    name = {}  # словарь    Имя игроков
    users = cur.execute('SELECT user_id,elo,name FROM {} '.format(bd_user), )

    for user in users:
        a.append(str(user[0]))
        s[str(user[0])] = user[1]
        name[str(user[0])] = user[2]

    # if dbg_info_in_console == 'yes':print('список игроков: a =' + str(a))
    # if dbg_info_in_console == 'yes': print('рейтинг игроков: s =' + str(s))

    raunds = {i: abs(s[i[0]] - s[i[1]]) for i in itertools.combinations(a, 2)}
    # print('raunds= ',raunds)
    # if dbg_info_in_console == 'yes': print(f'Все комбинации для игры с разницей рейтинга: \n{raunds}')
    sorted_tuple = sorted(raunds.items(), key=lambda x: x[1])
    # if dbg_info_in_console == 'yes': print(f'Отсортированно по разнице рейтинга: \n{sorted_tuple}')
    filter = []
    pari = []
    pari_n = []
    for i in sorted_tuple:

        if (i[0][0] not in filter) and (i[0][1] not in filter):
            filter.append(i[0][0])
            filter.append(i[0][1])
            pari_n.append((name[i[0][0]], name[i[0][1]]))
            pari.append((i[0][0], i[0][1]))

    if dbg_info_in_console == 'yes':
        print(f' Пары для игры \n{pari_n}')
        print(f' Этот ID не играет сегодня {set(a) - set(filter)}, его имя {name[list(set(a) - set(filter))[0]]}')
     #   non_in_game_id = []
     #   non_in_game_id.append(set(a) - set(filter))
        non_in_game_id = set(a) - set(filter)
    return [pari,non_in_game_id]



#  for i in pari:
#      if dbg_info_in_console == 'yes': print(f'msg {i[0]} против {i[1]}')
#      message = await ctx.send('<@' + i[0] + '> vs <@' + i[1] + '>') #отправляем и получаем ИД сообщения о матче
#      if dbg_info_in_console == 'yes': print('DBG_ создан матч ' + str(message.id))
#      cur.execute('INSERT id,user_1,user_2 INTO {} VALUES(?, ?, ?)'.format(bd_match),(message.id,i[0],i[1])).fetchone()
#      base.commit()

@bot.command(brief='Тестовая команда для создания матчей')
async def t2(ctx):
    pari = create_new_matchs()
    if dbg_info_in_console == 'yes': print(f'DBG pari  =   {str(pari[1])}  type {type(pari)}')
    for i in pari[0]:
        if dbg_info_in_console == 'yes': print(f'msg {i[0]} против {i[1]}')
        message = await ctx.send('<@' + i[0] + '> vs <@' + i[1] + '>')  # отправляем и получаем ИД сообщения о матче
        if dbg_info_in_console == 'yes': print('DBG_ создан матч ' + str(message.id))
        # cur.execute('INSERT INTO {} VALUES(?, ?, ?, ?, ?, ?, ?, ?)'.format(bd_match),(message.id,i[0],i[1],0,0,0,0,0)).fetchone()
        cur.execute('INSERT INTO {} (id,user_1,user_2) VALUES(?, ?, ?)'.format(bd_match),(message.id, i[0], i[1])).fetchone()
        base.commit()
    pari[1] = str(pari[1])
   # print(f' DBG t2 str(pari[1][3:-2]) = {str(pari[1][2:-2])} type = {type(pari[1])}')
    await ctx.send('<@' + str(pari[1][2:-2]) + '> остался без соперника')  # один остался без пары

@bot.command(brief='Create challenge', description='Через пробел указать противника')
async def vs(ctx, arg=None):
    print(f'DBG_ [INFO] !VS arg = {str(arg)}')
    if arg == None: return
    # name_server = ctx.guild.name
    user1_id = ctx.author.id
    now = datetime.datetime.now()
    user2_id = (str(arg[3:-1]))
    user2_chk = cur.execute('SELECT user_id FROM {} WHERE user_id == ?'.format(bd_user), (user2_id,)).fetchone()
    if user2_chk == None or str(user1_id) == user2_id: return

    challenge = rtn_name_on_id(user1_id)
    # print(f' arg = {str(arg)} user2_id = {str(user2_id)}')

    if dbg_info_in_console == 'yes': print(f'msg {rtn_name_on_id(user1_id)} против {rtn_name_on_id(user2_id)}')
    message = await ctx.send('<@' + str(user1_id) + '> vs <@' + str(user2_id) + '>')  # отправляем и получаем ИД сообщения о матче
    if dbg_info_in_console == 'yes': print('DBG_ [INFO] VS создан матч ' + str(message.id))
    cur.execute('INSERT INTO {} (id,user_1,user_2,challenge) VALUES(?, ?, ?, ?)'.format(bd_match),(message.id, str(user1_id), user2_id, challenge)).fetchone()
    base.commit()
    print(f'DBG_ [INFO] VS message.id={message.id} user1_id={user1_id} user2_id={user2_id}')
    print(f'DBG_ [INFO] VS message.id={type(message.id)} user1_id={type(user1_id)} user2_id={type(user2_id)}')


def rtn_name_on_id(user_id):
    return (str(cur.execute('SELECT name FROM {} WHERE user_id == ?'.format(bd_user), (user_id,)).fetchone())[2:-3])


def end_match_elo(win_user_id, los_user_id, id_mess):
    name_users = cur.execute('SELECT user_1,user_2 FROM {} WHERE id == ?'.format(bd_match), (id_mess,)).fetchone()
    user1 = cur.execute('SELECT * FROM {} WHERE user_id == ?'.format(bd_user), (str(name_users[0]),)).fetchone()
    user2 = cur.execute('SELECT * FROM {} WHERE user_id == ?'.format(bd_user), (str(name_users[1]),)).fetchone()

    if user1[6] == None or user2[6] == None:
        print(f'DBG_ 🚩 [ERROR]  ELO None:  user1= {str(user1[6])} user2= {str(user2[6])}')
        return
    print(
        f'DBG_ 🚩 [INFO] end_match_elo : win_user_id={str(win_user_id)} {type(win_user_id)} los_user_id={str(los_user_id)} {type(los_user_id)} id_mess={str(id_mess)} {type(id_mess)}')

    # result = [int(user1[6]), int(user2[6])]
    if dbg_info_in_console == 'yes': print('DBG_ 🚩 fnk elo == ' + str(win_user_id) + ' los = ' + str(los_user_id))

    if win_user_id == name_users[0]:  # если победительИД равен юзеру1
        if dbg_info_in_console == 'yes': print('DBG_ 🚩 1 win_user_id == ' + str(name_users[0]))
        result = elo.get_new_ratings([int(user1[6]), int(user2[6])])
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[0]), str(user1[0]),)).fetchone()
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[1]), str(user2[0]),)).fetchone()
        base.commit()

    if win_user_id == name_users[1]:  # если победительИД равен юзеру2
        if dbg_info_in_console == 'yes': print('DBG_ 🚩 2 win_user_id == ' + str(name_users[1]))
        result = elo.get_new_ratings([int(user2[6]), int(user1[6])])
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[0]), str(user1[0]),)).fetchone()
        cur.execute('Update {} set elo = ?  WHERE user_id == ?'.format(bd_user),(int(result[1]), str(user2[0]),)).fetchone()
        base.commit()

    print(
        f'DBG_ 🚩 new ELO:  {rtn_name_on_id(user1[0])}={(str(result[0]))} : {rtn_name_on_id(user2[0])}={(str(result[1]))} ')


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

    #  id           user1       user2       check_1     check_2     win1        win2        match_end
    #  id_match[0]  id_match[1] id_match[2] id_match[3] id_match[4] id_match[5] id_match[6] id_match[7]
    if not id_match == None and str(check_emoji) == '👍' and not str(id_match[7]) == '1':  # отмена готовности
        if int(id_match[1]) == user_id:
            await channel.send('<@' + str(user_id) + '> отменил готовность')
            cur.execute('Update {} set check_1 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()
        if int(id_match[2]) == user_id:
            await channel.send('<@' + str(user_id) + '> отменил готовность')
            cur.execute('Update {} set check_2 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()

    if not id_match == None and str(check_emoji) == '✅' and not str(id_match[7]) == '1':  # отмена победы
        if int(id_match[1]) == user_id:
            await channel.send('<@' + str(user_id) + '> отменил победу')
            cur.execute('Update {} set win1 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()
        if int(id_match[2]) == user_id:
            await channel.send('<@' + str(user_id) + '> отменил победу')
            cur.execute('Update {} set win2 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()

    if not id_match == None and str(check_emoji) == '🚫' and not str(id_match[7]) == '1':  # отмена проигрыша
        if int(id_match[1]) == user_id:
            await channel.send('<@' + str(user_id) + '> отменил проигрыш')
            cur.execute('Update {} set win1 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()
        if int(id_match[2]) == user_id:
            await channel.send('<@' + str(user_id) + '> отменил проигрыш')
            cur.execute('Update {} set win2 = ? WHERE id == ?'.format(bd_match), ('0', id_mess,)).fetchone()
            base.commit()


@bot.command(pass_context=True, brief='Тестовая команда')
async def tst_list(ctx):
    a = []
    users = cur.execute('SELECT user_id,elo,name FROM {} '.format(bd_user), )

    for user in users:
        a.append(str(user[2]) + ' ' + str(user[1]) + '')
    await ctx.send(a)


#  embed = discord.Embed(
#     description = f'You drew: {first_random_item}\nand\n{second_random_item}',
#     colour = discord.Colour.from_rgb(47,128,49)
#      )
# embed.set_footer(text="Bot of Greed", icon_url="link")
# await ctx.send(embed=embed)


bot.run('OTEyNTUzODAwNzU2MjQ0NTAw.YZxn9A.cGoeXkIovgzT38Xfs2yKU1JkSHM')
