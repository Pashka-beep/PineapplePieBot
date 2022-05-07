import discord
from discord.ext import commands
import sqlite3
import requests
import json
import random

bot = commands.Bot(command_prefix='!', help_command=None)

connection = sqlite3.connect("data/discord_data.sqlite")
cursor = connection.cursor()

@bot.event
async def on_ready():
    print("Бот готов, на вылет!")


@bot.command(name='help')
async def help(ctx):
    embed = discord.Embed(title='Помощь!',
                          description=f'**__Вот и помощь пришла__**\n\n'
                                      f'**Весёлости!**\n'
                                      f'!coin - монетка\n'
                                      f'!fox - случайное изображение лиса\n\n'
                                      f'**Экономика!**\n'
                                      f'!shop - магазин с ролями сервера\n'
                                      f'!balance/bal/cash/ - показать баланс пользователя\n'
                                      f'!buy/buy-role (пинг роли) - купить роль\n'
                                      f'!leaderboard/lb - вывод лидерборда\n\n'
                                      f'**Команды администрации**\n'
                                      f'!add-shop (роль) (стоимость) - добавить роль в магазин\n'
                                      f'!remove-shop (роль) - удалить роль из магазина\n'
                                      f'!award (юзер) (количество) - добавить ананасы\n'
                                      f'!take (юзер) (количество/all) - убрать ананасы\n\n'
                                      f'**Пока это всё, ананасовый пирог будет дорабатываться!**')
    await ctx.send(embed=embed)


"""Весёлости!"""
@bot.command(name='fox')
async def fox(ctx):
    response = requests.get('https://some-random-api.ml/img/fox')
    json_data = json.loads(response.text)
    embed = discord.Embed()
    embed.set_image(url=json_data['link'])
    await ctx.send(embed=embed)


@bot.command(name='coin')
async def coin(ctx):
    a = random.choice(['орёл', 'решка'])
    if a == 'орёл':
        embed = discord.Embed(title='Выпал орёл!')
    else:
        embed = discord.Embed(title='Выпала решка!')
    await ctx.send(embed=embed)


"""Экономика!"""
@bot.event
async def on_message(message):
    min_length = 15
    info = cursor.execute(f'SELECT * FROM user_info WHERE server_id={message.guild.id} and user_id={message.author.id}')
    if info.fetchone() is None:
        sqlite_insert_query = f"""INSERT INTO user_info
                                      (server_id, user_id, balance, bank)
                                      VALUES ({message.guild.id}, {message.author.id}, {0}, {0})"""
        cursor.execute(sqlite_insert_query)
        connection.commit()
    if len(message.content) >= min_length:
        sqlite_insert_query = f"""UPDATE user_info SET balance = balance + {int((len(message.content) * 100 // min_length) / 100)} 
                                  WHERE server_id={message.guild.id} and user_id={message.author.id}"""
        cursor.execute(sqlite_insert_query)
        connection.commit()
    await bot.process_commands(message)


@bot.command(aliases=['balance', 'cash', 'bal'])
async def __balance(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send(embed=discord.Embed(
            description=f"""Баланс пользователя **{ctx.author}** составляет **{cursor.execute(f"SELECT balance FROM user_info WHERE server_id={ctx.guild.id} and user_id={ctx.author.id}").fetchone()[0]}:pineapple:**"""
        ))
    else:
        await ctx.send(embed=discord.Embed(
            description=f"""Баланс пользователя **{member}** составляет **{cursor.execute(f"SELECT balance FROM user_info WHERE server_id={ctx.guild.id} and user_id={member.id}").fetchone()[0]}:pineapple:**"""
        ))


@bot.command(aliases=['shop'])
async def __shop(ctx):
    embed = discord.Embed(title='Магазин ролей')
    info = cursor.execute(f"SELECT role_id, cost FROM shop WHERE server_id={ctx.guild.id}")
    if info.fetchone() is None:
        embed = discord.Embed(title='Товаров нет')
    for row in cursor.execute(f"SELECT role_id, cost FROM shop WHERE server_id={ctx.guild.id}"):
        if ctx.guild.get_role(row[0]) is not None:
            embed.add_field(
                name=f"Стоимость **{row[1]} :pineapple:**",
                value=f"Вы приобрете роль {ctx.guild.get_role(row[0]).mention}",
                inline=False
            )
        else:
            pass
    await ctx.send(embed=embed)


@bot.command(aliases=['buy', 'buy-role'])
async def __buy(ctx, role: discord.Role = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль, которую вы желаете приобрести")
    else:
        if role in ctx.author.roles:
            await ctx.send(f"**{ctx.author}**, у вас уже имеется данная роль")
        elif cursor.execute(f"SELECT cost FROM shop WHERE role_id={role.id}").fetchone()[0] > \
                cursor.execute(f"SELECT balance FROM user_info WHERE user_id={ctx.author.id}").fetchone()[0]:
            await ctx.send(f"**{ctx.author}**, у вас недостаточно средств для покупки данной роли")
        else:
            await ctx.author.add_roles(role)
            cursor.execute("UPDATE user_info SET balance = balance - {} WHERE user_id = {}".format(
                cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0],
                ctx.author.id))
            connection.commit()

            await ctx.message.add_reaction('✅')


@bot.command(aliases=['leaderboard', 'lb'])
async def __leaderboard(ctx):
    embed = discord.Embed(title='Топ 10 сервера')
    counter = 0

    for row in cursor.execute(
            f"SELECT user_id, balance FROM user_info WHERE server_id = {ctx.guild.id} ORDER BY balance DESC LIMIT 10"):
        counter += 1
        embed.add_field(
            name=f'# {counter} | {await bot.fetch_user(row[0])}',
            value=f'Баланс: {row[1]}',
            inline=False
        )

    await ctx.send(embed=embed)


"""Команды администраторов."""


@bot.command(aliases=['remove-shop'])
@commands.has_permissions(administrator=True)
async def __remove_shop(ctx, role: discord.Role = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль, которую вы желаете удалить из магазина")
    else:
        cursor.execute(f"DELETE FROM shop WHERE role_id = {role.id}")
        connection.commit()

        await ctx.message.add_reaction('✅')


@bot.command(aliases=['award'])
@commands.has_permissions(administrator=True)
async def __award(ctx, member: discord.Member = None, amount: int = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите пользователя, которому желаете выдать определенную сумму")
    else:
        if amount is None:
            await ctx.send(f"**{ctx.author}**, укажите сумму, которую желаете начислить на счет пользователя")
        elif amount < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 1 :pineapple:")
        else:
            cursor.execute(f"""UPDATE user_info SET balance = balance + {amount}
                                WHERE server_id={ctx.guild.id} and user_id={member.id}""")
            connection.commit()
            await ctx.message.add_reaction('✅')


@bot.command(aliases=['take'])
@commands.has_permissions(administrator=True)
async def __take(ctx, member: discord.Member = None, amount=None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите пользователя, у которого желаете отнять сумму денег")
    else:
        if amount is None:
            await ctx.send(f"**{ctx.author}**, укажите сумму, которую желаете отнять у счета пользователя")
        elif amount == 'all':
            cursor.execute(f"UPDATE user_info SET balance = {0} WHERE user_id = {member.id}")
            connection.commit()

            await ctx.message.add_reaction('✅')
        elif int(amount) < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 1 :pineapple:")
        else:
            cursor.execute(f"UPDATE user_info SET balance = balance - {int(amount)} WHERE user_id = {member.id}")
            connection.commit()

            await ctx.message.add_reaction('✅')


@bot.command(aliases=['add-shop'])
@commands.has_permissions(administrator=True)
async def __add_shop(ctx, role: discord.Role = None, cost: int = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль, которую вы желаете внести в магазин")
    else:
        if cost is None:
            await ctx.send(f"**{ctx.author}**, укажите стоимость для данной роли")
        elif cost < 0:
            await ctx.send(f"**{ctx.author}**, стоимость роли не может быть такой маленькой")
        else:
            cursor.execute(f"INSERT INTO shop VALUES ({ctx.guild.id}, {role.id}, {cost})")
            connection.commit()

            await ctx.message.add_reaction('✅')


bot.run('TOKEN')
