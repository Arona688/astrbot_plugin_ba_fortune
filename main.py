"""BA 运势 —— 碧蓝档案主题的每日运势插件。

指令：/ba运势（ba 大小写不敏感）
规则：随机 1~5 星，对应 凶 / 吉 / 小吉 / 中吉 / 大吉，
      给出一段基沃托斯风格的解读，并附配图。
"""

from __future__ import annotations

import datetime
import hashlib
import json

import aiohttp
import random
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star, StarTools, register

PLUGIN_NAME = "astrbot_plugin_ba_fortune"

VERDICTS = {
    5: ("大吉", "今天整个基沃托斯都站在你这边"),
    4: ("中吉", "顺顺利利，偶有小确幸"),
    3: ("小吉", "平稳的一天，适合按计划走"),
    2: ("吉", "有点小波折，但都能化解"),
    1: ("凶", "今天请低调，别乱跑"),
}

STAR_WEIGHTS = [8, 17, 25, 30, 20]

STUDENT_LINES: dict[str, list[str]] = {'阿罗娜': ['老师，今天的日程我已经排好啦！', '有我在，老师放心就好。', '要不要先看一眼今天的计划？'],
 '普拉娜': ['已记录。这一天值得备份。', '老师，我在整理前天、昨天和现在。', '数据不会说谎，请相信我。'],
 '爱露': ['便利屋68，随时为您服务！', '委托费可以商量，真的！', '这次的任务，我们一定办好。'],
 '艾米': ['老师，今天的训练计划呢？', '重量再加一点也没问题。', '身体是最诚实的。'],
 '晴奈': ['老师～要不要喝杯咖啡？', '我用的是自己的豆子哦。', '慢慢喝，别急。'],
 '日富美': ['补习部今天也照常营业。', '老师，这次我一定及格！', '再讲一遍这道题好不好？'],
 '日奈': ['风纪委员会，开始工作。', '……老师，别给我添麻烦。', '今天的巡逻，我来带队。'],
 '星野': ['呜嘿～老师来对策委员会坐坐吧。', '大叔我啊，今天也想偷懒。', '阿拜多斯，交给我看着。'],
 '伊织': ['这种程度也敢来？', '让开点，我要动手了。', '……别误会，我只是在训练。'],
 '真纪': ['老师，看我的新作品！', '颜料又沾到衣服上了。', '这幅画，我想画完。'],
 '妮露': ['道具部随时待命！', '这个机关绝对不会炸……对吧？', '三、二、一——发射！'],
 '泉': ['食堂今天有新品！', '这个好吃，那个也好吃！', '老师也来一口？'],
 '白子': ['老师，要一起去沙漠吗？', '枪我已经擦好了。', '——出发吧。'],
 '瞬': ['课上完了，收拾一下。', '别把我当成小孩子。', '……我可不是小孩子。'],
 '堇': ['修行，从今天开始。', '老师，请安静一点。', '心静，手就稳了。'],
 '鹤城': ['要一起修行吗？', '……我不会输的。', '战场在哪？我这就去。'],
 '泉奈': ['忍法·今天也要努力！', '泉奈会一直在老师身边。', '老师，忍者的修行开始了！'],
 '爱丽丝': ['勇者大人，冒险开始啦！', '老师，一起打副本吗？', '光啊——！'],
 '绿': ['姐姐，别乱翻我的东西。', '老师，这张图要修一下。', '画画的时候，我很专注。'],
 '切里诺': ['红冬的纪律，不容松懈。', '冷吗？靠近一点。', '这里由我守着。'],
 '柚子': ['老、老师……能别看我吗？', '我、我会努力的……', '游戏……要一起玩吗？'],
 '梓': ['今天也要保持优雅。', '老师，您的领带歪了。', '优雅，是一种习惯。'],
 '小春': ['老师！我没有在偷懒！', '这次考试我会及格的！', '补、补习部的事，交给我！'],
 '夏': ['老师，要不要来杯特调？', '今天的心情不错。', '这杯，只给你调。'],
 '若藻': ['老师，祭典要一起吗？', '百鬼夜行的夜晚最棒了！', '热闹一点才像祭典！'],
 '三森': ['忍术修行，开始了。', '百鬼夜行的规矩要守。', '师出有名，行得正。'],
 '忧': ['图书室的书我整理好了。', '请安静一点，好吗？', '书里的人，比现实温柔。'],
 '日向': ['老师，要一起祈祷吗？', '愿今天也平安无事。', '主会听见的。'],
 '真里奈': ['老师，功课我写完了。', '山海经的课程很难呢。', '再难的题，我也要弄懂。'],
 '宫子': ['SRT的训练开始了。', '任务优先，感情其次。', '……这是命令。'],
 '美游': ['老师，我能帮上忙吗？', '对不起……我太没用了。', '我会努力的，真的。'],
 '月咏': ['老师，今天也要出门吗？', '我会保护好你的。', '警戒中，请勿靠近。'],
 '美咲': ['……别看我，我只是路过。', '吵死了。…不过，留下来也可以。', '这种温柔，我不习惯。'],
 '亚津子': ['老师，今天也要一起吗？', '我没事的，真的。', '……谢谢你陪着我。'],
 '纱织': ['老师，别靠近我。', '……谢谢你。', '阿里乌斯的事，我自己来。'],
 '和纱': ['老师，看招——开个玩笑。', '别担心，我会保护你。', '来，笑一个。'],
 '心奈': ['老师，今天也辛苦了。', '要不要休息一下？', '身体要紧哦。'],
 '诺亚': ['数据整理完毕，请过目。', '这次的记录，我备份了三份。', '数字不会骗人。'],
 '时雨': ['老师，账目我核对完了。', '钱要花在刀刃上哦。', '这本账，我盯着。'],
 '美祢': ['礼数是必要的。', '三一的荣耀，不容玷污。', '请端正你的态度。'],
 '未花': ['老师，茶会准备好了。', '今天的红茶是特调的哦。', '坐下来，慢慢聊。'],
 '惠': ['老师，要一起做点什么吗？', '今天也很有精神呢。', '手脚快点，才不浪费时间。'],
 '樱子': ['老师，今天的祈祷您来吗？', '愿神明保佑。', '安静地听着就好。'],
 '时': ['老师，时间到了哦。', '这一天，也要好好记录。', '……一秒也不能浪费。'],
 '小雪': ['老师，要一起玩吗？', '今天也下雪了呢。', '雪地里，走路要小心。'],
 '果穗': ['老师，文件已经整理好了。', '请确认一下这份报告。', '细节不能出错。'],
 '玲纱': ['老师，侦查结果出来了。', '这次也没问题。', '情报已经确认。'],
 '瑠海': ['老师，要来一杯吗？', '大人的世界，很复杂呢。', '喝一杯，忘一天。'],
 '南': ['老师，红茶泡好了。', '请慢用。', '温度刚好。'],
 '芽瑠': ['老师，今天的训练呢？', '我还能再跑十圈！', '体力就是一切！'],
 '一花': ['老师，要喝一杯吗？', '放松点，别那么紧张。', '来，坐这边。'],
 '霞': ['老师，今天的行程有变。', '请按我说的做。', '计划，我已经改好了。'],
 '御坂美琴': ['老师，这种程度不算什么。', '别、别误会，只是顺手。', '电击——开玩笑的。'],
 '食蜂操祈': ['老师，要听我的吗？', '今天也要乖乖的哦。', '……别想太多。'],
 '紫': ['老师，今天要画画吗？', '颜色……很难决定呢。', '这一笔，我想画得慢一点。'],
 '莲华': ['老师，今天也来泡温泉吗？', '水温刚刚好。', '温泉，是最好的药。'],
 '桔梗': ['老师，任务完成了。', '接下来，交给我吧。', '刀已出鞘。'],
 '海香': ['老师，今天的海很平静。', '要不要一起出去？', '海风吹着，很舒服吧。'],
 '绮罗罗': ['老师，新游戏到了！', '这次绝对好玩！', '一起开一局？'],
 '白子＊恐怖': ['老师……今天也很安静呢。', '沙漠里，只有风的声音。', '……别回头。'],
 '丽情': ['老师，今天的计划是？', '我会好好完成的。', '交给我，别担心。'],
 '千明': ['老师，要一起调查吗？', '真相只有一个！', '线索，我已经找齐了。'],
 '圣娅': ['老师，占卜的结果出来了。', '命运……似乎站在你这边。', '牌面，不会说谎。'],
 '丽': ['今天也请好好休息。', '请好好休息。', '今天也请注意身体。'],
 '光': ['老师，要走这边哦。', '姐姐她……又在忙了。', '跟着我，不会走丢。'],
 '望': ['老师，需要人手吗？', '我会努力的！', '有什么我能帮忙的吗？'],
 '名草': ['老师，百鬼夜行今天很热闹。', '要不要一起走走？', '街上的人，都很友善。'],
 '绘里': ['老师，这幅画怎么样？', '还差一点就完成了。', '颜色，我很讲究。'],
 '庚': ['老师，今天的巡逻报告。', '我没有偷懒。', '路线已经走完了。'],
 '美代': ['老师，要一起发呆吗？', '今天的天很蓝呢。', '什么都不做，也很好。'],
 '冬': ['老师，冷吗？', '多穿一点比较好。', '冬天，也有冬天的好。'],
 '昴': ['老师，今天的训练开始了。', '我不会输的。', '再来一次！'],
 '贵音': ['老师，要听我唱歌吗？', '今天的嗓子状态不错。', '这首歌，送给老师。'],
 '柯伊': ['老师……可以靠近一点吗？', '我、我鼓起勇气了。', '……谢谢你不嫌弃我。'],
 '木乃香': ['老师，今天的茶会。', '请尝尝这块点心。', '茶要趁热喝。'],
 '丽奈': ['老师，行动开始了。', '请跟在我后面。', '别出声。'],
 '妮可': ['老师，要去看夜景吗？', '今晚的星星很漂亮。', '这里看星星最好了。'],
 '胡桃': ['老师，找到线索了！', '这个案子交给我。', '细节里藏着真相。'],
 '心': ['老师，今天也要开心哦。', '笑一笑嘛。', '开心最重要。'],
 '琴音': ['老师，今天的演出准备好了！', '应援团，随时待命！', '大家——加油！'],
 '安娜': ['老师，今天的行程安排好了。', '请不要太勉强自己。', '我会帮你的。'],
 '䌷': ['老师，今天想去哪里？', '我都可以哦。', '跟你一起就好。'],
 '茜': ['老师，我找到线索了！', '这次也交给我吧。', '这个谜题，有意思。'],
 '千世': ['老师，今天要拍照吗？', '这个角度最好看！', '笑一下，三、二、一！'],
 '明里': ['老师，今天的巡逻！', '守法是每个学生的义务。', '秩序，要有人守护。'],
 '莲见': ['老师，今天的祈祷。', '愿您平安。', '……请保重。'],
 '野宫': ['老师！自警团集合！', '巡逻就交给我们！', '阿拜多斯，由我守护！'],
 '佳代子': ['老师，今天的课结束了。', '……算了，随你。', '便利屋的事，交给我。'],
 '睦月': ['老师～来玩游戏吧？', '这次我保证不作弊！', '输了可不许赖账哦。'],
 '纯子': ['老师，今天也来帮忙吗？', '清扫任务，开始！', '这里，交给我打扫！'],
 '芹香': ['别误会，我才不是特意等你！', '钱……这个月有点紧。', '柴关拉面，今天也营业！'],
 '椿': ['老师，可以睡着吗？', '呼……呼……', '……啊，我睡着了吗？'],
 '优香': ['老师的报销单，我看过了哦。', '这个月的预算……我们得谈谈。', '算术不会骗人。'],
 '桃': ['老师老师！来看这个新游戏！', '这关卡超难的！', '一起玩嘛！'],
 '桐乃': ['今天的巡逻报告在这里。', '瓦尔基里的纪律。', '巡逻路线已确认。'],
 '红叶': ['老师，今天画点什么？', '红叶的颜色最好看了。', '这一笔，是秋天。'],
 '春香': ['老师，今天的课……好难。', '我会努力的。', '……别丢下我。'],
 '明日奈': ['老师，一起去吃点什么吧？', '有我在，放心。', '跟着我，不会迷路！'],
 '琴里': ['老师，应援团随时待命！', '今天也元气满满！', '加油——！'],
 '铃美': ['老师，魔法要开始了哦。', '别眨眼。', '……骗你的，是枪。'],
 '菲娜': ['今天的巡逻，我也去！', '我跑得很快的！', '追得上我吗？'],
 '巴': ['任务完成，请过目。', '需要我做点什么吗？', '任务交接完毕。'],
 '吹雪': ['老师，今天也一起偷懒吧？', '啊，被抓到了。', '效率工作，省下时间休息。'],
 '满': ['老师，今天要吃饭吗？', '我做了很多哦。', '吃饱了才有力气。'],
 '伊吹': ['老师，今天的计划呢？', '我准备好了。', '……可以开始了吗？'],
 '青叶': ['老师，要不要一起看云？', '今天的天空很漂亮。', '云的颜色，每天都不一样。'],
 '兰舞': ['老师，要一起跳舞吗？', '节奏感不错嘛！', '来，跟着节拍！'],
 '御伽': ['老师，今天的修行。', '请多指教。', '妖怪的传说，要听吗？'],
 '响': ['老师，今天的应援！', '大家都要加油！', '声音，要传得更远！'],
 '花凛': ['射击训练，随时可以开始。', '命中。……下一个。', '风向，我看清了。'],
 '纱绫': ['训练，我准备好了。', '我会跟上的！', '……别小看人。'],
 '真白': ['狙击手已经就位。', '风向……修正完毕。', '目标，锁定。'],
 '初音未来': ['老师，今天要唱歌吗？', '大家一起来吧！', '这首歌，一起唱！'],
 '亚子': ['风纪委员会的工作，交给我吧。', '记录完毕，回头再算账。', '规矩，就是规矩。'],
 '濑名': ['老师，今天也要出去吗？', '我陪你。', '受伤的话，交给我。'],
 '千寻': ['老师，数据整理好了。', '黑客的工作，交给我。', '防火墙，我来看。'],
 '咲': ['狙击点已经选好了。', '别乱动，会打偏的。', '……屏住呼吸。'],
 '枫': ['老师，今天也要努力！', '百鬼夜行，出发！', '修行，从打扫开始。'],
 '伊吕波': ['老师，今天要去哪里？', '我开车送你吧。', '……系好安全带。'],
 '日和': ['老师，今天的天空很蓝。', '要不要一起晒晒太阳？', '这样的日子，很难得。'],
 '萌绘': ['老师！今天也要加油哦！', 'SRT最棒的！', '一起训练吧！'],
 '日鞠': ['老师，今天的实验！', '这次绝对没问题！', '数据……应该没错。']}

STUDENTS = [(name, lines) for name, lines in STUDENT_LINES.items()]

PLACES = [
    "阿拜多斯高中·对策委员会", "千年科学学园·自修室", "格黑娜学园·风纪委员会",
    "三一综合学园·茶会", "百鬼夜行·樱花中庭", "山海经·学生食堂",
    "瓦尔基里警察学校·派出所", "夏莱·老师的办公室", "基沃托斯车站",
    "黑市·巷子深处", "阿拜多斯·沙漠公路", "游戏开发部·部室",
    "正义实现委员会·本部", "便利屋68·事务所",
]

ITEMS = [
    "阿罗娜的护目镜", "老师的教师证", "白子的突击步枪",
    "优香的账本", "日奈的红色围巾", "便利屋68的传单",
    "千年的能量饮料", "三一的红茶", "山海经的包子",
    "星野的靠枕", "阿罗娜的日程表", "夏莱的备用印章",
    "睦月的游戏手柄", "泉奈的忍者卷轴", "未花的茶具",
]

CLUBS = [
    "对策委员会", "风纪委员会", "茶会", "便利屋68", "游戏开发部",
    "正义实现委员会", "自警团", "补习部", "美食研究会", "温泉开发部",
]

COLORS = [
    "阿罗娜蓝", "白子白", "星野粉", "日奈红", "优香绿",
    "未花金", "普拉娜灰", "三一奶白", "格黑娜暗红",
]

PERIODS = [
    "清晨（06:00-09:00）", "上午（09:00-12:00）", "午后（12:00-15:00）",
    "黄昏（15:00-18:00）", "夜晚（18:00-22:00）", "深夜（22:00-02:00）",
]

GOOD = [
    "批改作业", "在夏莱整理文件", "陪学生巡校", "去便利屋68下单委托",
    "在食堂抢限定甜点", "给阿罗娜买草莓牛奶", "检查学生的社团活动",
    "去三一茶会喝一杯红茶", "陪白子去沙漠兜风", "和优香对账",
    "去游戏开发部试玩新作", "陪星野在委员会午睡",
]

BAD = [
    "单挑头盔团", "在格黑娜随便问路", "惹风纪委员会",
    "试玩千年未完成的发明", "跟温泉开发部抢地盘",
    "深夜一个人去黑市", "让阿罗娜单独管账", "随便动白子的枪",
    "替便利屋68背锅", "在茶会上讨论格黑娜", "跟美食研究会抢食堂",
]

KEYWORDS = [
    "稳", "冲刺", "休息", "整理", "出击", "陪伴", "补觉", "摸鱼",
    "收拾残局", "小冒险", "安静", "热闹",
]

STORIES = {
    5: [
        "老师今天状态绝佳。刚进夏莱，办公桌上就堆满了学生送来的慰问品；"
        "阿罗娜把日程排得满满当当，却全是“陪学生玩”的行程。",
        "出门被三个社团同时邀请，连头盔团都主动让路——"
        "今天的老师，是基沃托斯最受欢迎的人。",
        "阿罗娜的指纹锁今天一次就认出了老师，她高兴得原地转了三圈。"
        "普拉娜默默把这一天标记为“值得备份的日子”。",
    ],
    4: [
        "一切顺利。委托按时完成，学生也格外听话，"
        "只是优香在走廊尽头盯着老师的报销单，笑得有点危险。",
        "去便利屋68的路上遇到白子，她破天荒没提议去沙漠，"
        "而是说“今天陪老师走走吧”。",
        "三一的红茶今天格外香，连风纪委员会都难得没来查岗。"
        "老师心想：这大概就是和平吧。",
    ],
    3: [
        "平稳的一天。上午处理文件，下午陪学生，傍晚被阿罗娜拉着复述日程，"
        "一切都在计划内，除了那只突然飞进办公室的鸽子。",
        "没什么大事，但小惊喜不断：食堂多给了一勺菜，"
        "走廊上有人偷偷把老师的名字写进社团留言板。",
        "今天适合按部就班。老师完成了所有委托，"
        "只是回夏莱时发现阿罗娜把咖啡换成了草莓牛奶。",
    ],
    2: [
        "有点小波折。出门被头盔团拦了一次，"
        "好在白子刚好路过——虽然她只是想去沙漠，顺路而已。",
        "上午还算顺利，下午在格黑娜问路时被风纪委员会盯上，"
        "老师解释了半天才脱身，亚子在旁边笑得直不起腰。",
        "今天最好别乱跑。便利屋68的委托出了岔子，"
        "阿露道歉的姿态很标准，赔偿单递得也很熟练。",
    ],
    1: [
        "老师今天请低调。刚出夏莱就撞见头盔团在附近转悠，"
        "阿罗娜在终端里小声提醒：“老师，要不今天别出门了？”",
        "诸事不宜。去黑市买材料被认出来，回程还被温泉开发部误当成地皮勘探员，"
        "普拉娜表示：已记录，不建议复制这一天。",
        "今天的学生缘有点微妙。学生们轮流来办公室“关心”老师，"
        "其实是来看老师是不是真像传闻里那样倒霉。",
    ],
}

ADVICE = {
    5: "宜：主动出击，多接几个委托，今天的运气够用。",
    4: "宜：推进积压的工作，顺便奖励自己一杯甜的。",
    3: "宜：按计划行事，不要临时改行程。",
    2: "宜：带伞、早点回夏莱，遇事先找阿罗娜商量。",
    1: "宜：待在办公室批作业，把外出的委托交给学生。",
}


def _bar(value: int, width: int = 10) -> str:
    filled = max(0, min(width, round(value / 100 * width)))
    return "▰" * filled + "▱" * (width - filled)


@register(PLUGIN_NAME, "chen", "碧蓝档案主题的每日运势", "1.2.0")
class BAFortunePlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self.data_dir = Path(StarTools.get_data_dir(PLUGIN_NAME))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / "daily.json"
        self.plugin_dir = Path(__file__).resolve().parent
        self._midnight_task = None
        self.qq = None  # qqoffice_expand 服务门面（可选）
        self._qq_unsubs: list = []
        self._start_midnight_task()

    def _try_bind_qq(self) -> bool:
        try:
            meta = self.context.get_registered_star("astrbot_plugin_qqoffice_expand")
            if not (meta and meta.activated and meta.star_cls):
                return False
            getter = getattr(meta.star_cls, "get_service", None)
            if not callable(getter):
                return False
            service = getter(api_version=1)
            if service is None:
                return False
            self.qq = service
            logger.info("[BA运势] 已接入 qqoffice_expand")
            return True
        except Exception as exc:
            logger.info(f"[BA运势] 未接入 qqoffice_expand: {exc}")
            return False

    @filter.on_plugin_loaded()
    async def _on_plugin_loaded(self, metadata):
        if self.qq is None:
            self._try_bind_qq()

    async def initialize(self):
        self._try_bind_qq()

    async def _send_card_with_buttons(self, event: AstrMessageEvent, png_path: str) -> bool:
        """把卡片图上传 QQ 素材库，用 markdown 图片 + 指令按钮一条发出。"""
        plat = str(event.get_platform_name() or "")
        if not plat.startswith("qq_official"):
            return False
        if self.qq is None and not self._try_bind_qq():
            return False
        try:
            from pathlib import Path as _Path

            from PIL import Image as _Image

            raw = _Path(png_path).read_bytes()
            md5 = hashlib.md5(raw).hexdigest()
            sha1 = hashlib.sha1(raw).hexdigest()
            with _Image.open(png_path) as im:
                w, h = im.size
            view = self.qq.for_event(event)
            prep = await view.call(
                "POST",
                "/v2/media-images/prepare",
                json={
                    "file_name": "fortune.png",
                    "file_size": len(raw),
                    "content_type": "image/png",
                    "md5": md5,
                    "sha1": sha1,
                },
            )
            upload_id = prep.get("upload_id") or ""
            presigned = prep.get("presigned_url") or ""
            if not (upload_id and presigned):
                logger.warning(f"[BA运势] 素材 prepare 异常：{prep}")
                return False
            async with aiohttp.ClientSession(trust_env=True) as sess:
                async with sess.put(
                    presigned,
                    data=raw,
                    headers={"Content-Type": "image/png"},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as r:
                    if r.status not in (200, 201, 204):
                        logger.warning(f"[BA运势] 素材直传失败：{r.status}")
                        return False
                    etag = (r.headers.get("ETag") or "").strip('"')
            done = await view.call(
                "POST",
                "/v2/media-images/complete",
                json={"upload_id": upload_id, "md5": etag or md5},
            )
            url = done.get("url") or ""
            image_id = done.get("image_id") or ""
            if not url:
                logger.warning(f"[BA运势] 素材 complete 异常：{done}")
                return False
            kb = self.qq.kb()
            kb.row(
                self.qq.btn("🎲 再抽一次", "/ba运势", type=2, enter=True),
                self.qq.btn("📊 今日榜单", "/ba运势榜", type=2, enter=True),
            )
            md = self.qq.md_image(url, width=w, height=h)
            await view.send_rich(markdown=self.qq.md(md), keyboard=kb.build())
            if image_id:
                try:
                    await view.call(
                        "DELETE", f"/v2/media-images/{image_id}/delete"
                    )
                except Exception:
                    pass
            logger.info("[BA运势] 卡片+按钮已同条发送")
            return True
        except Exception as exc:
            logger.warning(f"[BA运势] 卡片+按钮发送失败：{exc}")
            return False

    async def _send_action_buttons(self, event: AstrMessageEvent) -> None:
        """发一条带指令按钮的提示：再抽一次 / 榜单。"""
        plat = str(event.get_platform_name() or "")
        logger.info(f"[BA运势] 尝试发送操作按钮，platform={plat!r}")
        if not plat.startswith("qq_official"):
            logger.info("[BA运势] 非 QQ 官方平台，跳过操作按钮")
            return
        if self.qq is None and not self._try_bind_qq():
            logger.info("[BA运势] 未绑定 qqoffice_expand，跳过操作按钮")
            return
        try:
            kb = self.qq.kb()
            kb.row(
                self.qq.btn("🎲 再抽一次", "/ba运势", type=2, enter=True),
                self.qq.btn("📊 今日榜单", "/ba运势榜", type=2, enter=True),
            )
            view = self.qq.for_event(event)
            await view.send_rich(
                markdown=self.qq.md("想看别人的运势，或者再抽一次？点下面 👇"),
                keyboard=kb.build(),
            )
            logger.info("[BA运势] 操作按钮已发送")
        except Exception as exc:
            logger.warning(f"[BA运势] 发送操作按钮失败：{exc}")

    # ───────────────────────── 日期 ─────────────────────────
    @staticmethod
    def _now() -> datetime.datetime:
        """东八区当前时间（服务器时区变了也不会影响零点判定）。"""
        try:
            from zoneinfo import ZoneInfo

            return datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
        except Exception:
            return datetime.datetime.now()

    @classmethod
    def _today(cls) -> str:
        return cls._now().date().isoformat()

    def _start_midnight_task(self) -> None:
        """零点清零任务。"""
        import asyncio

        async def _loop():
            while True:
                now = self._now()
                nxt = (now + datetime.timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                wait = max(1.0, (nxt - now).total_seconds())
                await asyncio.sleep(wait)
                try:
                    cache = self._load_cache()
                    cache["date"] = self._today()
                    cache["users"] = {}
                    self._save_cache(cache)
                    logger.info("[BA运势] 已到零点，今日查询次数已清零")
                except Exception as exc:
                    logger.warning(f"[BA运势] 零点清零失败: {exc}")

        try:
            self._midnight_task = asyncio.create_task(_loop())
        except Exception as exc:
            logger.warning(f"[BA运势] 启动零点任务失败: {exc}")
            self._midnight_task = None

    # ───────────────────────── 数据 ─────────────────────────
    def _load_cache(self) -> dict:
        try:
            if self.cache_file.is_file():
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_cache(self, data: dict) -> None:
        try:
            self.cache_file.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning(f"[BA运势] 保存缓存失败: {exc}")

    def _image_for(self, star: int) -> str:
        configured = str(self.config.get("images_dir") or "").strip()
        base = Path(configured) if configured else self.plugin_dir / "images"
        if not base.is_dir():
            return ""
        exts = (".png", ".jpg", ".jpeg", ".webp")
        for stem in (str(star), f"{star}星", "any"):
            for ext in exts:
                path = base / f"{stem}{ext}"
                if path.is_file():
                    return str(path)
        for path in sorted(base.iterdir()):
            if path.suffix.lower() in exts:
                return str(path)
        return ""

    def _roll(self, user_id: str) -> dict:
        star = random.choices([1, 2, 3, 4, 5], weights=STAR_WEIGHTS, k=1)[0]
        verdict, tagline = VERDICTS[star]
        student, lines = random.choice(STUDENTS)
        line = random.choice(lines)
        luck = {
            "学生缘": min(100, max(5, star * 18 + random.randint(-12, 12))),
            "老师体力": min(100, max(5, star * 16 + random.randint(-14, 14))),
            "欧气": min(100, max(5, star * 17 + random.randint(-16, 16))),
            "钱包厚度": min(100, max(5, star * 15 + random.randint(-18, 18))),
        }
        return {
            "star": star,
            "verdict": verdict,
            "tagline": tagline,
            "luck": luck,
            "student": student,
            "line": line,
            "place": random.choice(PLACES),
            "item": random.choice(ITEMS),
            "club": random.choice(CLUBS),
            "color": random.choice(COLORS),
            "period": random.choice(PERIODS),
            "number": random.randint(1, 99),
            "keyword": random.choice(KEYWORDS),
            "good": random.choice(GOOD),
            "bad": random.choice(BAD),
            "story": random.choice(STORIES[star]),
            "advice": ADVICE[star],
        }

    def _compose(self, result: dict) -> str:
        star = result["star"]
        show_stars = bool(self.config.get("show_stars", True))
        star_text = f"{'★' * star}{'☆' * (5 - star)}" if show_stars else ""
        lines = [
            f"🔮 今日 BA 运势　{star_text}".rstrip(),
            f"【{result['verdict']}】{result['tagline']}",
            f"关键词：{result['keyword']}",
            "",
            f"👧 幸运学生：{result['student']}",
            f"　「{result['line']}」",
            f"🏫 幸运社团：{result['club']}",
            f"📍 幸运地点：{result['place']}",
            f"🎒 幸运道具：{result['item']}",
            f"🔢 幸运数字：{result['number']}　🎨 幸运色：{result['color']}",
            f"⏰ 幸运时段：{result['period']}",
            "────────────────",
            f"学生缘　　{_bar(result['luck']['学生缘'])} {result['luck']['学生缘']}%",
            f"老师体力　{_bar(result['luck']['老师体力'])} {result['luck']['老师体力']}%",
            f"欧气　　　{_bar(result['luck']['欧气'])} {result['luck']['欧气']}%",
            f"钱包厚度　{_bar(result['luck']['钱包厚度'])} {result['luck']['钱包厚度']}%",
            "────────────────",
            f"✅ 宜：{result['good']}",
            f"🚫 忌：{result['bad']}",
            "",
            f"📖 解读：{result['story']}",
            f"💡 {result['advice']}",
        ]
        if star == 5:
            lines.append("✨ 阿罗娜偷偷给你加了一颗星。")
        return "\n".join(lines)

    # ───────────────────────── 渲染 ─────────────────────────
    CARD_CSS = """
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif; }
    .card {
      width: 720px; position: relative; overflow: hidden;
      padding: 26px 28px 22px; color: #1f2329;
      background: linear-gradient(135deg, #eef7ff 0%, #fbfeff 46%, #fff7f0 100%);
    }
    .emblem {
      position: absolute; right: 34px; top: 96px; width: 152px;
      opacity: .42; pointer-events: none;
    }
    .content { position: relative; z-index: 2; }
    .glass {
      background: rgba(255, 255, 255, .72);
      border: 1px solid rgba(150, 195, 240, .34);
      border-radius: 16px;
    }
    .top { display: flex; align-items: center; justify-content: space-between; }
    .logo { width: 138px; height: auto; display: block; }
    .ring {
      width: 54px; height: 54px; border-radius: 50%; object-fit: cover;
      border: 3px solid #fff; box-shadow: 0 3px 10px rgba(90,150,230,.22);
    }
    .date { font-size: 12px; color: #7b8794; letter-spacing: .5px; }
    .label {
      margin-top: 14px; font-size: 11px; letter-spacing: 3px; color: #93a1b0;
      text-transform: uppercase;
    }
    .stars-row { margin-top: 6px; display: flex; align-items: center; gap: 12px; }
    .stars { font-size: 34px; color: #ffb400; letter-spacing: 3px; line-height: 1; }
    .verdict {
      font-size: 19px; font-weight: 700; color: #fff; padding: 5px 16px;
      border-radius: 999px; background: linear-gradient(135deg, #4f9dff, #2f6fed);
      box-shadow: 0 4px 12px rgba(47, 111, 237, .30);
    }
    .tagline { margin-top: 10px; font-size: 15px; color: #46515e; }
    .keyword {
      display: inline-block; margin-top: 10px; padding: 4px 14px; border-radius: 999px;
      background: rgba(255, 255, 255, .85); border: 1px solid rgba(150, 195, 240, .5);
      font-size: 13px; color: #2f6fed; font-weight: 600;
    }
    .student { margin-top: 20px; display: flex; align-items: center; gap: 14px; padding: 12px 14px; }
    .avatar {
      width: 66px; height: 66px; border-radius: 50%; flex: 0 0 66px; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
      background: #dce9fb; color: #fff; font-size: 24px; font-weight: 700;
      border: 3px solid #fff; box-shadow: 0 4px 14px rgba(90, 150, 230, .22);
    }
    .avatar img { width: 100%; height: 100%; object-fit: cover; }
    .sname { font-size: 21px; font-weight: 700; letter-spacing: .5px; }
    .sline { margin-top: 4px; font-size: 14px; color: #5b6675; }
    .grid {
      margin-top: 12px; padding: 12px 16px; display: grid;
      grid-template-columns: 1fr 1fr; gap: 9px 18px;
    }
    .cell { font-size: 13.5px; color: #4a5563; }
    .cell b { color: #1f2329; font-weight: 700; }
    .bars { margin-top: 12px; padding: 12px 16px; }
    .bar { display: flex; align-items: center; gap: 10px; margin-bottom: 7px; font-size: 13px; }
    .bar:last-child { margin-bottom: 0; }
    .bar .label2 { width: 78px; color: #5b6675; }
    .track {
      flex: 1; height: 9px; border-radius: 6px; overflow: hidden;
      background: #ffffff; border: 1px solid rgba(150, 195, 240, .45);
    }
    .fill { height: 100%; border-radius: 6px; background: linear-gradient(90deg, #7fbcff, #2f6fed); }
    .pct { width: 42px; text-align: right; color: #4a5563; }
    .rule { margin-top: 12px; padding: 12px 16px; font-size: 13.5px; line-height: 1.7; }
    .good { color: #1a7f4b; font-weight: 600; }
    .bad { color: #c0392b; font-weight: 600; }
    .story { margin-top: 12px; padding: 14px 16px; font-size: 14px; line-height: 1.75; color: #38414d; }
    .story b { color: #2f6fed; }
    .foot { margin-top: 12px; font-size: 12px; color: #8a94a3; text-align: right; }
    .cardfoot {
      margin-top: 12px; display: flex; align-items: center;
      justify-content: space-between; gap: 12px;
    }
    .cardfoot .foot { margin-top: 0; flex: 1; }
    .cmdchip {
      display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto;
      padding: 6px 12px; border-radius: 999px; font-size: 12px;
      color: #2f6fed; background: rgba(255,255,255,.88);
      border: 1px solid rgba(120,170,235,.45);
      box-shadow: 0 1px 4px rgba(90,150,230,.12); letter-spacing: .3px;
    }
    .cmdchip b { font-weight: 700; }
    """

    # ───────────────────────── 素材 / 头像 ─────────────────────────
    def _asset_uri(self, name: str, mime: str = "image/png") -> str:
        """把 assets/<name> 转成 data URI；不存在返回空。"""
        try:
            import base64

            path = self.plugin_dir / "assets" / name
            if path.is_file():
                return f"data:{mime};base64," + base64.b64encode(
                    path.read_bytes()
                ).decode()
        except Exception as exc:
            logger.info(f"[BA运势] 读取素材 {name} 失败: {exc}")
        return ""

    def _bg_data_uri(self) -> str:
        return self._asset_uri("bg.png")

    def _default_avatar_uri(self) -> str:
        return self._asset_uri("user.png")

    def _official_appid(self, event: AstrMessageEvent) -> str:
        client = getattr(event, "client", None) or getattr(event, "bot", None)
        platform = getattr(client, "platform", None)
        for source in (platform, client, getattr(event, "platform_meta", None)):
            appid = getattr(source, "appid", None)
            if appid:
                return str(appid).strip()
        return ""

    def _avatar_url(self, event: AstrMessageEvent) -> str:
        """构造用户头像 URL（不下载）。"""
        from urllib.parse import quote

        uid = str(event.get_sender_id() or "").strip()
        if not uid:
            return ""
        appid = self._official_appid(event)
        if not uid.isdigit() and appid:
            return (
                f"https://q.qlogo.cn/qqapp/{quote(appid, safe='')}"
                f"/{quote(uid, safe='')}/0"
            )
        if uid.isdigit():
            return f"https://q1.qlogo.cn/g?b=qq&nk={uid}&s=100"
        return ""

    async def _fetch_uri(self, url: str) -> str:
        """下载图片并转成 data URI；失败返回空串。"""
        try:
            import base64

            import aiohttp

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8), trust_env=True
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return ""
                    data = await resp.read()
                    if len(data) < 200:
                        return ""
                    return "data:image/png;base64," + base64.b64encode(data).decode()
        except Exception as exc:
            logger.info(f"[BA运势] 头像下载失败 {url}: {exc}")
            return ""

    async def _user_avatar_uri(self, event: AstrMessageEvent) -> str:
        """取发送者头像（官方 bot 用 qqapp 接口，QQ 号用 qlogo）。"""
        if not hasattr(self, "_avatar_cache"):
            self._avatar_cache: dict[str, str] = {}
        uid = str(event.get_sender_id() or "").strip()
        if not uid:
            return ""
        if uid in self._avatar_cache:
            return self._avatar_cache[uid]
        url = self._avatar_url(event)
        if not url:
            return ""
        uri = await self._fetch_uri(url)
        if uri:
            self._avatar_cache[uid] = uri
        return uri

    def _student_icon_uri(self, name: str) -> str:
        """读取学生头像。

        优先 ``assets/students/<学生名>.png``（开发时散装），
        否则从 ``assets/students.zip`` 里取（发布用，单文件分发）。
        """
        import base64

        if not hasattr(self, "_icon_cache"):
            self._icon_cache: dict[str, str] = {}
        cached = self._icon_cache.get(name)
        if cached is not None:
            return cached

        data = b""
        try:
            path = self.plugin_dir / "assets" / "students" / f"{name}.png"
            if path.is_file():
                data = path.read_bytes()
        except Exception:
            data = b""

        if not data:
            try:
                import zipfile

                zip_path = self.plugin_dir / "assets" / "students.zip"
                if zip_path.is_file():
                    with zipfile.ZipFile(zip_path) as zf:
                        try:
                            data = zf.read(f"{name}.png")
                        except KeyError:
                            data = b""
            except Exception as exc:
                logger.info(f"[BA运势] 读取学生头像包失败 {name}: {exc}")

        uri = (
            "data:image/png;base64," + base64.b64encode(data).decode()
            if data
            else ""
        )
        self._icon_cache[name] = uri
        return uri

    def _card_html(self, result: dict, avatar_uri: str = "") -> str:
        import html as _html

        star = result["star"]
        stars = "★" * star + "☆" * (5 - star)
        bars = ""
        for label, value in result["luck"].items():
            bars += (
                f'<div class="bar"><div class="label2">{label}</div>'
                f'<div class="track"><div class="fill" style="width:{value}%"></div></div>'
                f'<div class="pct">{value}%</div></div>'
            )

        icon_uri = self._student_icon_uri(result["student"])
        if icon_uri:
            student_avatar = f'<img src="{icon_uri}" />'
        else:
            student_avatar = _html.escape(result["student"][:1])

        avatar = avatar_uri or self._default_avatar_uri()
        arona = f'<img class="ring" src="{avatar}" />' if avatar else ""
        bg = self._bg_data_uri()
        logo_uri = self._asset_uri("logo.png")
        emblem_uri = self._asset_uri("schale.png")
        illust_uri = self._asset_uri("arona.png")

        bg_css = (
            ".card{background-image:"
            "linear-gradient(rgba(255,255,255,.72),rgba(255,255,255,.80)),"
            f'url(\"{bg}\");'
            "background-size:cover;background-position:center top;}"
            if bg
            else ""
        )
        illust = ""
        today = self._now().strftime("%Y-%m-%d")

        return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" />
<style>{self.CARD_CSS}{bg_css}</style></head><body>
<div class="card">
  {illust}
  <img class="emblem" src="{emblem_uri}" />

  <div class="content">
    <div class="top">
      <img class="logo" src="{logo_uri}" />
      {arona}
    </div>
    <div class="date" style="margin-top:6px">{today} · 基沃托斯</div>

    <div class="label">Today's Fortune</div>
    <div class="stars-row">
      <div class="stars">{stars}</div>
      <div class="verdict">{_html.escape(result['verdict'])}</div>
    </div>
    <div class="tagline">{_html.escape(result['tagline'])}</div>
    <div class="keyword">关键词 · {_html.escape(result['keyword'])}</div>

    <div class="student glass">
      <div class="avatar">{student_avatar}</div>
      <div>
        <div class="sname">幸运学生 · {_html.escape(result['student'])}</div>
        <div class="sline">「{_html.escape(result['line'])}」</div>
      </div>
    </div>

    <div class="grid glass">
      <div class="cell">🏫 幸运社团 · <b>{_html.escape(result['club'])}</b></div>
      <div class="cell">📍 幸运地点 · <b>{_html.escape(result['place'])}</b></div>
      <div class="cell">🎒 幸运道具 · <b>{_html.escape(result['item'])}</b></div>
      <div class="cell">🔢 幸运数字 · <b>{result['number']}</b></div>
      <div class="cell">🎨 幸运色 · <b>{_html.escape(result['color'])}</b></div>
      <div class="cell">⏰ 幸运时段 · <b>{_html.escape(result['period'])}</b></div>
    </div>

    <div class="bars glass">{bars}</div>

    <div class="rule glass">
      <div class="good">✅ 宜 · {_html.escape(result['good'])}</div>
      <div class="bad">🚫 忌 · {_html.escape(result['bad'])}</div>
    </div>

    <div class="story glass"><b>解读</b>　{_html.escape(result['story'])}</div>
    <div class="cardfoot">
      <div class="cmdchip">📊 看全群运势 · 发 <b>/ba运势榜</b></div>
      <div class="foot">{_html.escape(result['advice'])}</div>
    </div>
  </div>
</div></body></html>"""

    BOARD_CSS = """
    * { box-sizing: border-box; }
    body { margin: 0; background: #eef6ff; font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif; }
    .board {
      width: 760px; padding: 24px 26px 20px; overflow: hidden;
      background: linear-gradient(160deg, #eaf4ff 0%, #fbfeff 48%, #fff8f1 100%);
      position: relative;
    }
    .bemblem {
      position: absolute; right: 16px; top: 10px; width: 150px;
      opacity: .38; pointer-events: none;
    }
    .board::before {
      content: ""; position: absolute; left: 0; right: 0; top: 0; height: 6px;
      background: linear-gradient(90deg, #9fd0ff, #ffc2dc 55%, #ffd166 100%);
    }
    .head { display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 2; }
    .left { display: flex; align-items: center; gap: 10px; }
    .brand { font-size: 11px; letter-spacing: 2px; color: #9aa6b2; margin-top: 2px; }
    .logo { width: 210px; height: auto; display: block; margin-bottom: 6px; }
    .title { font-size: 22px; font-weight: 700; }
    .date { font-size: 13px; color: #7b8794; text-align: right; }
    .date .time { display: block; font-size: 11px; color: #a3adba; margin-top: 2px; }
    .sub { margin-top: 6px; font-size: 13px; color: #6b7683; }

    .stats { display: flex; gap: 10px; margin-top: 14px; position: relative; z-index: 2; }
    .stat {
      flex: 1; padding: 10px 12px; border-radius: 12px;
      background: rgba(255,255,255,.78); border: 1px solid rgba(150,195,240,.32);
    }
    .stat .k { font-size: 11px; color: #8a94a3; letter-spacing: 1px; }
    .stat .v { font-size: 20px; font-weight: 700; color: #2f6fed; margin-top: 2px; }
    .stat .v small { font-size: 12px; font-weight: 500; color: #8a94a3; margin-left: 2px; }

    .chart {
      margin-top: 12px; padding: 12px 14px; border-radius: 14px;
      background: rgba(255,255,255,.72); border: 1px solid rgba(150,195,240,.28);
      position: relative; z-index: 2;
    }
    .chart .ctitle { font-size: 12px; color: #7b8794; margin-bottom: 8px; letter-spacing: 1px; }
    .barrow { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
    .barlabel { width: 74px; font-size: 12px; color: #ffb400; letter-spacing: 1px; }
    .bartrack { flex: 1; height: 10px; border-radius: 6px; background: #e8f0fa; overflow: hidden; }
    .barfill { height: 100%; border-radius: 6px; }
    .barfill.s5 { background: linear-gradient(90deg,#ffd166,#ff9f43); }
    .barfill.s4 { background: linear-gradient(90deg,#a5d8ff,#5b8def); }
    .barfill.s3 { background: linear-gradient(90deg,#b2f2bb,#51cf66); }
    .barfill.s2 { background: linear-gradient(90deg,#ffe3e3,#ff8787); }
    .barfill.s1 { background: linear-gradient(90deg,#e9ecef,#adb5bd); }
    .barval { width: 26px; text-align: right; font-size: 12px; color: #6b7683; }

    .list { margin-top: 14px; position: relative; z-index: 2; }
    .item {
      display: flex; align-items: center; gap: 12px; padding: 11px 14px;
      background: rgba(255, 255, 255, .74);
      border: 1px solid rgba(150, 195, 240, .32); border-radius: 14px;
      margin-bottom: 8px; position: relative; z-index: 2;
    }
    .item.top1 { border-color: #ffd166; box-shadow: 0 2px 8px rgba(255,190,80,.20); background: rgba(255,252,240,.9); }
    .item.top2 { border-color: #d7dde5; }
    .item.top3 { border-color: #e8c7a5; }
    .rank { width: 34px; text-align: center; font-size: 18px; font-weight: 700; color: #4a5563; }
    .icon { width: 46px; height: 46px; border-radius: 50%; overflow: hidden; flex: 0 0 46px; background: #dbe9fb; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px; font-weight: 700; }
    .icon img { width: 100%; height: 100%; object-fit: cover; }
    .who { flex: 1; min-width: 0; }
    .name { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    .tag { font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 6px; }
    .tag.luck { color: #b8860b; background: #fff3cd; border: 1px solid #ffe08a; }
    .tag.bad { color: #8a94a3; background: #eef1f5; border: 1px solid #dde3ea; }
    .meta { font-size: 12px; color: #7b8794; margin-top: 2px; }
    .right { text-align: right; }
    .stars { font-size: 16px; color: #ffb400; letter-spacing: 2px; display: block; }
    .verdict { font-size: 13px; color: #2f6fed; font-weight: 700; }
    .foot { margin-top: 12px; font-size: 12px; color: #8a94a3; display: flex; justify-content: space-between; }
    """

    def _board_html(self, rows: list[dict], avatars: dict | None = None) -> str:
        import html as _html

        avatars = avatars or {}
        total = len(rows)
        stars_all = [int(r.get("star", 0) or 0) for r in rows]
        avg = (sum(stars_all) / total) if total else 0.0
        luck = sum(1 for x in stars_all if x >= 4)
        unlucky = sum(1 for x in stars_all if x <= 2)
        dist = {n: sum(1 for x in stars_all if x == n) for n in range(5, 0, -1)}

        items = []
        medals = ["🥇", "🥈", "🥉"]
        for idx, rec in enumerate(rows[:15]):
            star = int(rec.get("star", 0) or 0)
            stars = "★" * star + "☆" * (5 - star)
            rank = medals[idx] if idx < 3 else f"{idx + 1}"
            name = _html.escape(str(rec.get("name", "?")))
            student = _html.escape(str(rec.get("student", "")))
            verdict = _html.escape(str(rec.get("verdict", "")))
            tag = ""
            if star >= 5:
                tag = '<span class="tag luck">欧皇</span>'
            elif star <= 2:
                tag = '<span class="tag bad">非酋</span>'
            icon_uri = avatars.get(str(rec.get("name", ""))) or ""
            if not icon_uri:
                icon_uri = self._default_avatar_uri()
            icon = (
                f'<img src="{icon_uri}" />'
                if icon_uri
                else _html.escape(str(rec.get("name", "?"))[:1] or "?")
            )
            cls = "item" + (f" top{idx + 1}" if idx < 3 else "")
            items.append(
                f'<div class="{cls}">'
                f'<div class="rank">{rank}</div>'
                f'<div class="icon">{icon}</div>'
                f'<div class="who"><div class="name">{name}{tag}</div>'
                f'<div class="meta">幸运学生 · {student}</div></div>'
                f'<div class="right"><span class="stars">{stars}</span>'
                f'<span class="verdict">{verdict}</span></div>'
                f"</div>"
            )

        bars = []
        for n in range(5, 0, -1):
            count = dist[n]
            pct = (count / total * 100) if total else 0.0
            bars.append(
                f'<div class="barrow"><div class="barlabel">{"★" * n}</div>'
                f'<div class="bartrack"><div class="barfill s{n}" style="width:{pct:.1f}%"></div></div>'
                f'<div class="barval">{count}</div></div>'
            )

        now = self._now()
        today = now.strftime("%Y-%m-%d")
        clock = now.strftime("%H:%M")
        max_stars = "★" * 5
        logo_uri = self._asset_uri("logo.png")
        emblem_uri = self._asset_uri("schale.png")
        return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" />
<style>{self.BOARD_CSS}</style></head><body>
<div class="board">
  <img class="bemblem" src="{emblem_uri}" />
  <div class="head">
    <div class="left">
      <div>
        <img class="logo" src="{logo_uri}" />
        <div class="title">今日运势榜</div>
        <div class="brand">基沃托斯 · 今日谁最欧</div>
      </div>
    </div>
    <div class="date">{today}<span class="time">更新于 {clock}</span></div>
  </div>
  <div class="sub">共 {total} 人参与 · 最高 {max_stars}</div>

  <div class="stats">
    <div class="stat"><div class="k">参与人数</div><div class="v">{total}<small>人</small></div></div>
    <div class="stat"><div class="k">平均星级</div><div class="v">{avg:.1f}<small>★</small></div></div>
    <div class="stat"><div class="k">大吉率</div><div class="v">{(luck / total * 100) if total else 0:.0f}<small>%</small></div></div>
    <div class="stat"><div class="k">非酋</div><div class="v">{unlucky}<small>人</small></div></div>
  </div>

  <div class="chart">
    <div class="ctitle">星级分布</div>
    {"".join(bars)}
  </div>

  <div class="list">{"".join(items)}</div>
  <div class="foot"><span>🏆 前 15 名 · 每天 0 点重置</span><span>发 /ba运势 参与</span></div>
</div></body></html>"""
    async def _render_board(self, rows: list[dict], avatars: dict | None = None) -> str:
        import tempfile
        from pathlib import Path as _Path

        from playwright.async_api import async_playwright

        html_text = self._board_html(rows, avatars)
        tmp_html = _Path(tempfile.mkstemp(suffix=".html")[1])
        tmp_png = _Path(tempfile.mkstemp(suffix=".png")[1])
        tmp_html.write_text(html_text, encoding="utf-8")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox"])
                page = await browser.new_page(
                    viewport={"width": 760, "height": 1000}, device_scale_factor=2
                )
                await page.goto(tmp_html.as_uri())
                await page.wait_for_timeout(300)
                element = await page.query_selector(".board")
                if element is None:
                    await page.screenshot(path=str(tmp_png), full_page=True)
                else:
                    await element.screenshot(path=str(tmp_png))
                await browser.close()
            return str(tmp_png)
        finally:
            try:
                tmp_html.unlink(missing_ok=True)
            except Exception:
                pass

    async def _render_card(self, result: dict, avatar_uri: str = "") -> str:
        import tempfile
        from pathlib import Path as _Path

        from playwright.async_api import async_playwright

        html_text = self._card_html(result, avatar_uri)
        tmp_html = _Path(tempfile.mkstemp(suffix=".html")[1])
        tmp_png = _Path(tempfile.mkstemp(suffix=".png")[1])
        tmp_html.write_text(html_text, encoding="utf-8")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox"])
                page = await browser.new_page(
                    viewport={"width": 760, "height": 900}, device_scale_factor=2
                )
                await page.goto(tmp_html.as_uri())
                await page.wait_for_timeout(300)
                element = await page.query_selector(".card")
                if element is None:
                    await page.screenshot(path=str(tmp_png), full_page=True)
                else:
                    await element.screenshot(path=str(tmp_png))
                await browser.close()
            return str(tmp_png)
        finally:
            try:
                tmp_html.unlink(missing_ok=True)
            except Exception:
                pass

    # ───────────────────────── 指令 ─────────────────────────
    @staticmethod
    def _group_key(event: AstrMessageEvent) -> str:
        return str(event.get_group_id() or "").strip() or "private"

    def _record_key(self, event: AstrMessageEvent, user_id: str) -> str:
        return f"{self._group_key(event)}:{user_id}"

    def _is_unlimited(self, event: AstrMessageEvent, uid: str) -> bool:
        """是否不受每日次数限制：配置名单 + AstrBot 管理员。"""
        raw = str(self.config.get("unlimited_users", "") or "")
        ids = {x.strip() for x in raw.replace("，", ",").split(",") if x.strip()}
        if uid and uid in ids:
            return True
        if bool(self.config.get("admin_unlimited", True)):
            try:
                if event.is_admin():
                    return True
            except Exception:
                pass
        return False

    @filter.regex(r"(?i)^[\s/]*ba运势$")
    async def ba_fortune(self, event: AstrMessageEvent):
        """今日 BA 运势。"""
        event.stop_event()
        user_id = str(event.get_sender_id() or "")
        today = self._today()
        limit = int(self.config.get("daily_limit", 1) or 0)

        cache = self._load_cache()
        if cache.get("date") != today:
            cache = {"date": today, "users": {}}
        users = cache.setdefault("users", {})

        key = self._record_key(event, user_id)
        rec = users.get(key)
        if isinstance(rec, int):
            rec = {"n": rec}
        rec = dict(rec or {})
        used = int(rec.get("n", 0) or 0)

        if limit > 0 and used >= limit and not self._is_unlimited(event, user_id):
            yield event.plain_result(
                "今天的运势已经抽过啦～\n阿罗娜说：贪心的人会被头盔团盯上的哦。"
            )
            return

        result = self._roll(user_id)
        name = (event.get_sender_name() or "").strip()
        rec.update(
            {
                "n": used + 1,
                "name": name or f"用户{user_id[-4:]}",
                "star": result["star"],
                "verdict": result["verdict"],
                "student": result["student"],
                "ts": self._now().isoformat(timespec="seconds"),
                "avatar": self._avatar_url(event),
            }
        )
        users[key] = rec
        self._save_cache(cache)

        text = self._compose(result)

        if bool(self.config.get("dynamic_card", True)):
            try:
                avatar = await self._user_avatar_uri(event)
                card = await self._render_card(result, avatar)
                if await self._send_card_with_buttons(event, card):
                    return
                yield event.image_result(card)
                return
            except Exception as exc:
                logger.warning(f"[BA运势] 动态卡片渲染失败，回退文字: {exc}")

        image = self._image_for(result["star"])
        chain: list = []
        if image:
            chain.append(Image(file=image))
        chain.append(Plain(text))
        yield event.chain_result(chain)

    @filter.regex(r"(?i)^[\s/]*ba运势榜$")
    async def ba_board(self, event: AstrMessageEvent):
        """今日运势榜。"""
        event.stop_event()
        cache = self._load_cache()
        if cache.get("date") != self._today():
            yield event.plain_result("今天还没有人抽运势哦～发 /ba运势 试试")
            return

        prefix = self._group_key(event) + ":"
        rows = [
            rec
            for key, rec in (cache.get("users") or {}).items()
            if key.startswith(prefix) and isinstance(rec, dict)
        ]
        if not rows:
            yield event.plain_result("本群今天还没有人抽运势哦～发 /ba运势 试试")
            return

        rows.sort(key=lambda r: (-int(r.get("star", 0) or 0), str(r.get("ts", ""))))
        top = rows[:15]

        avatars: dict[str, str] = {}
        for rec in top:
            url = str(rec.get("avatar") or "")
            if not url:
                continue
            uri = await self._fetch_uri(url)
            if uri:
                avatars[str(rec.get("name", ""))] = uri

        try:
            image = await self._render_board(top, avatars)
            yield event.image_result(image)
            return
        except Exception as exc:
            logger.warning(f"[BA运势] 榜单渲染失败，回退文字: {exc}")

        medals = ["🥇", "🥈", "🥉"]
        lines = [f"🏆 今日 BA 运势榜（{len(rows)} 人）", ""]
        for idx, rec in enumerate(rows[:15]):
            star = int(rec.get("star", 0) or 0)
            stars = "★" * star + "☆" * (5 - star)
            rank = medals[idx] if idx < 3 else f"{idx + 1}."
            lines.append(
                f"{rank} {rec.get('name', '?')}　{stars} "
                f"{rec.get('verdict', '')} · {rec.get('student', '')}"
            )
        if len(rows) > 10:
            lines.append(f"…… 还有 {len(rows) - 10} 人")
        lines.append("")
        lines.append("发 /ba运势 参与")
        yield event.plain_result("\n".join(lines))

    async def terminate(self):
        task = getattr(self, "_midnight_task", None)
        if task is not None:
            task.cancel()
        for unsub in getattr(self, "_qq_unsubs", []):
            try:
                unsub()
            except Exception:
                pass
        logger.info("[BA运势] 插件已卸载")
