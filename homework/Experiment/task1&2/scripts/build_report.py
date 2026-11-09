#!/usr/bin/env python3
"""以课程要求 DOCX 第 2、3 页的段落和页面设置生成同一份实验报告。

依赖：python-docx、Pillow。所有插图均来自 screenshots 中的真实窗口截图。
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
TEMPLATE = BASE.parent / "task-requirement/计算机操作系统实验要求.docx"
OUTPUT = BASE / "学号待填写_姓名待填写_OSEX12.docx"
doc = Document(TEMPLATE)
original = [deepcopy(p._p) for p in doc.paragraphs]
body = doc._element.body
for child in list(body):
    if child.tag != qn("w:sectPr"):
        body.remove(child)
# 清除原模板中未再使用的示例截图和超链接；保留样式、编号及页面设置。
for rel in list(doc.part.rels.values()):
    if rel.reltype.endswith(("/image", "/hyperlink")):
        doc.part.drop_rel(rel.rId)


def font(run, size=10.5, bold=False, family="楷体"):
    run.font.name = family
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), family)


def paragraph(text="", bold=False, size=10.5, center=False):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.widow_control = True
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font(p.add_run(text), size, bold)
    return p


def template_paragraph(index, text=None, size=11, title=False):
    """直接复用指定模板段落的楷体、对齐及段落格式。"""
    p = deepcopy(original[index])
    for x in list(p):
        if x.tag != qn("w:pPr"):
            p.remove(x)
    props = p.find(qn("w:pPr"))
    if props is not None:
        for x in list(props):
            if x.tag == qn("w:numPr"):
                props.remove(x)
    doc._body._body.insert_element_before(p, "w:sectPr")
    from docx.text.paragraph import Paragraph
    result = Paragraph(p, doc._body)
    font(result.add_run(text if text is not None else ""), size, True)
    result.paragraph_format.space_before = Pt(5)
    result.paragraph_format.space_after = Pt(5)
    result.paragraph_format.keep_with_next = True
    if title:
        result.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return result


def subheading(text):
    p = paragraph(text, bold=True, size=11)
    p.paragraph_format.keep_with_next = True
    return p


def commands(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.05
    p.paragraph_format.keep_together = True
    for i, line in enumerate(text.splitlines()):
        if i:
            p.add_run().add_break()
        font(p.add_run(line), 8.7, family="DejaVu Sans Mono")
    shade = OxmlElement("w:shd")
    shade.set(qn("w:fill"), "F5F5F5")
    p._p.get_or_add_pPr().append(shade)
    return p


figures = []


def picture(filename, caption, width=18.0):
    path = BASE / "screenshots" / filename
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width))
    cap = paragraph(caption, center=True, size=9.5)
    cap.paragraph_format.space_after = Pt(7)
    figures.append({"file": filename, "caption": caption,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "pixels": list(Image.open(path).size)})


def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    widths = ([1.5, 8.3, 6.2, 2.0] if len(headers) == 4 else
              [2.2, 15.8] if headers[0] == "目录" else [4.5, 13.5])
    for column, width in zip(t.columns, widths):
        column.width = Cm(width)
    props = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        edge = OxmlElement("w:" + side)
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "4")
        edge.set(qn("w:color"), "888888")
        borders.append(edge)
    props.append(borders)
    for cell, text in zip(t.rows[0].cells, headers):
        font(cell.paragraphs[0].add_run(text), 10, True)
    for values in rows:
        cells = t.add_row().cells
        for cell, text in zip(cells, values):
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.line_spacing = 1.1
            font(p.add_run(str(text)), 10)
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, width in zip(row.cells, widths):
            cell.width = Cm(width)
    return t


def page(label):
    p = paragraph(label, size=10, center=True)
    p.paragraph_format.page_break_before = True
    p.paragraph_format.keep_with_next = True


def identity():
    paragraph("学号：待填写    姓名：待填写    班级：待填写    实验日期：2026年11月10日", center=True)


# 实验一：模板第 2 页，原有四个一级栏目均保留。
paragraph("《计算机操作系统》上机实验报告 EX1", center=True, size=12, bold=True)
template_paragraph(18, "实验1 Linux的基本操作", title=True, size=13)
identity()
template_paragraph(19, "一、实验目的")
for n, text in enumerate(["了解Linux的文件系统结构。", "掌握Linux的基本操作命令。",
                          "掌握nano、tar和gzip等基本工具的使用。", "熟悉Linux下的C语言编译链接环境。"], 1):
    paragraph(f"{n}．{text}")
template_paragraph(24, "二、实验环境")
paragraph("PPT给定环境为Ubuntu 12.4（32位，简体中文）。本次实际环境为WSL2下的Ubuntu 24.04.2 LTS（x86_64），使用GCC 13.3.0、Bash 5.2、GNU Make 4.3和GNU nano 7.2。")
paragraph("按当前登录用户执行操作，主目录为/home/ovo155，对应题目示例中的/home/osstudy。终端截图使用白色背景，时间按Asia/Shanghai记录。")
template_paragraph(26, "三、实验内容")
subheading("1—2．查看根目录，在当前用户主目录建立A和bin")
paragraph("执行mkdir A bin创建两个目录。完整根目录清单及创建回显保存在logs/01-root-and-directories.log；图1节选根目录前8行，便于查看本机目录结构。")
picture("00-root-summary.png", "图1  当前用户主目录、系统位数、根目录清单节选与五个目录属性")
table(["目录", "意义"], [
    ("/bin", "存放基本用户命令；本机为指向usr/bin的符号链接。"),
    ("/etc", "保存系统和服务的配置文件。"),
    ("/home", "保存普通用户的主目录，如/home/ovo155。"),
    ("/dev", "提供设备节点，程序通过它们访问设备。"),
    ("/mnt", "通常用作临时挂载文件系统的挂载点。")])

page("实验1 Linux的基本操作（续）")
subheading("3—4．利用nano建立sum.c，退出后在控制台显示源码")
paragraph("执行nano A/sum.c，在编辑器中新建并保存程序。Ctrl+O写入文件，回车确认文件名，Ctrl+X退出。随后执行cat A/sum.c，确认保存内容完整；完整控制台回显另见screenshots/03-source-c.png及同名日志。")
paragraph("程序用fgets读取输入，strtol检查整型数及范围，利用n(n+1)/2计算1至n的和。乘法先提升为long long，避免int溢出；本实现接受0至2147483647，n=0时输出0，负数或非法输入报错。")
picture("02-nano-c.png", "图2  GNU nano中保存的完整C程序（41行，含输入检查与注释）", width=17.5)
paragraph("源码文件：src/sum.c。输入10时应得到10×11÷2=55；实际编译运行结果见下一页。")

page("实验1 Linux的基本操作（续）")
subheading("5—9．编译、复制、压缩、修改权限并删除A")
paragraph("将A/sum.c编译链接为A/sum，输入10验证结果为55，再将可执行文件复制到bin。用tar把A内的全部文件打包并gzip压缩到主目录sum.tar.gz；-C A表示先进入A，末尾的点表示包含A中的全部条目。")
picture("04-build-archive-permissions.png", "图3  严格编译、求和、复制、压缩、755权限及删除A后的再次运行")
table(["操作", "实际结果"], [
    ("gcc严格编译", "-std=c11 -Wall -Wextra -Wpedantic -Werror；未出现警告或错误。"),
    ("A/sum与bin/sum输入10", "两次输出均为1 + ... + 10 = 55。"),
    ("tar -czvf sum.tar.gz -C A .", "归档含./、./sum.c与./sum，生成在/home/ovo155。"),
    ("chmod 755 sum.tar.gz", "stat显示-rwxr-xr-x和755。"),
    ("rm -r -- A", "test确认A已删除；bin/sum仍能独立运行。")])
paragraph("755由7、5、5组成：所有者为rwx，所属组和其他用户均为r-x，因此只有所有者具有写权限，符合题目要求。压缩包一般无需执行位，本实验按题目明确要求保留该位。")
paragraph("sum.tar.gz及后续实验输出已复制到evidence/home中保存，原始终端命令与退出状态保存在logs中。")

page("实验1 Linux的基本操作（续）")
template_paragraph(37, "四、思考与实践")
subheading("1．如何解压.tar.gz文件？")
paragraph("先创建恢复目录，再执行tar -xzvf sum.tar.gz -C restore-ex1。其中-x解包，-z使用gzip，-v显示条目，-f指定压缩包。恢复后的sum.c与提交源码逐字节相同，恢复后的sum输入10仍输出55。")
picture("05-extract-and-owner.png", "图4  解压、源码比较、程序运行、所有者核对及块设备查看")
subheading("2．如何修改文件所有者，修改后效果如何？")
paragraph('命令格式为sudo chown 新用户:新组 文件；用ls -l或stat查看所有者、所属组。本次对练习文件执行chown "$(id -un):$(id -gn)" restore-ex1/sum.c，将其设置为当前用户和组，前后均为ovo155:ovo155。')
paragraph("若管理员把文件改属另一用户，文件的所有者身份随之变化；访问时按新的身份适用所有者、组或其他用户权限。chown通常不直接改写普通rwx位，某些特殊权限位可能被系统清除。")
subheading("3．如何挂载U盘等外部存储设备？")
paragraph("先用lsblk -f识别设备与分区，再创建挂载点并挂载，例如：")
commands("sudo mkdir -p /mnt/usb\nsudo mount /dev/sdX1 /mnt/usb\nfindmnt /mnt/usb\nsudo umount /mnt/usb")
paragraph("/dev/sdX1为示意占位，实际须替换为确认过的分区。本次未接入用于实验的U盘，故只检查了块设备，不把上述挂载步骤记作已执行操作；WSL下还可能需要先由宿主机附加设备。")

page("实验1 Linux的基本操作（续）")
subheading("4．尝试Ubuntu的图形化工具")
paragraph("在当前Ubuntu环境中实际打开下列图形程序，分别查看文件、浏览本地页面、阅读Word模板并尝试图形软件包管理器。图5直接截取运行中的窗口，软件包管理器以普通用户模式启动。")
picture("12-graphical-tools.png", "图5  文件管理器、浏览器、文字处理工具和图形软件包管理器")
table(["工具", "操作与观察"], [
    ("Thunar文件管理器", "打开restore-ex1目录，查看解压得到的sum与sum.c。"),
    ("NetSurf浏览器", "打开本地实验说明HTML，观察浏览器显示页面内容。"),
    ("LibreOffice Writer", "打开课程提供的实验要求.docx，查看模板及其分页。"),
    ("Synaptic软件包管理器", "作为软件中心类工具的替代，尝试普通用户模式下的包管理界面；未执行安装、删除或更新。")])
paragraph("本实验把同一组文件从命令行和图形界面分别查看：命令行适合记录和重复执行，图形工具便于直观浏览目录与文档。编译、归档、权限和解压结果均有实际输出可核对。")

# 实验二：模板第 3 页，无论实验一占多少页，此处均显式另起一页。
p = paragraph("《计算机操作系统》上机实验报告 EX2", center=True, size=12, bold=True)
p.paragraph_format.page_break_before = True
template_paragraph(44, "实验2 Linux的基本操作（续）", title=True, size=13)
identity()
template_paragraph(45, "一、实验目的")
for n, text in enumerate(["了解管道和重定向。", "熟悉基本的Linux脚本的编写。",
                          "熟悉基本的Makefile脚本的编写（选做内容一并完成）。"], 1):
    paragraph(f"{n}．{text}")
paragraph("实验环境同实验一：Ubuntu 24.04.2 LTS，Bash 5.2、GNU Make 4.3。按模板第3页保留“实验目的—实验内容—思考与实践”结构。")
template_paragraph(49, "二、实验内容")
subheading("1—3．生成主目录清单，管道筛选根目录日期，再合并文件")
commands('ls -l > list1.txt\nLC_ALL=C ls -lA --time-style=+%m-%d / | awk \'$6 == "04-16"\' > list2.txt\ncat list1.txt list2.txt > list.txt')
picture("06-pipes-and-lists.png", "图6  文件重定向、4月16日日期筛选、行数统计及合并验证", width=17)
counts = {name: len((BASE / "evidence/home" / name).read_bytes().splitlines())
          for name in ["list1.txt", "list2.txt", "list.txt"]}
paragraph(f"本次list1.txt为{counts['list1.txt']}行，list2.txt为{counts['list2.txt']}行，list.txt为{counts['list.txt']}行。根目录一级条目没有符合4月16日的修改日期，因此list2.txt为空，这是本机的真实筛选结果。cmp确认list.txt与两份清单顺序拼接后的内容完全一致。")
paragraph('用LC_ALL=C固定字段格式，--time-style=+%m-%d固定月份和日期，awk按第6列精确比较“04-16”，不限定年份；-A包含隐藏条目但排除.和..。这里筛选根目录直接包含的条目，不递归遍历。重定向先创建list1.txt，所以它自身也会出现在清单中。')

page("实验2 Linux的基本操作（续）")
subheading("4．利用nano编写求和脚本sum.sh")
paragraph("执行nano sum.sh，保存后退出，并用chmod +x sum.sh赋予执行权限。脚本通过read读取n，用条件判断验证输入；非法输入用date取得当前时间，追加到error.log并exit 5；有效输入将求和结果重定向到sum.r。")
picture("07-nano-shell.png", "图7  nano中保存的sum.sh；完整可编辑源码见src/sum.sh", width=17.5)
paragraph("使用>>追加日志，使用>写入本次结果。输入限制为32位正整数，求和由Bash 64位整数运算完成；先处理前导零，避免08被当作八进制。--choose-output分支供思考与实践使用，默认行为仍写入sum.r。")

page("实验2 Linux的基本操作（续）")
subheading("5．分别以-1和10为n运行，核对日志、结果及退出码")
picture("08-shell-required-cases.png", "图8  n=-1返回5并追加日志；n=10返回0并把55写入sum.r", width=17)
table(["输入", "error.log", "sum.r", "退出码"], [
    ("-1", "新增当前时间及Input Error！ n = -1", "首次非法运行后不存在", "5"),
    ("10", "保留上一条错误记录，不新增错误", "内容为55（带换行）", "0")])
paragraph("每次运行后立即执行code=$?保存退出状态，再查看文件，避免后续cat等命令覆盖$?。错误行满足题目要求的“<当前时间> Input Error！ n = <输入值>”格式。本次截图中的时间为2026-11-10，按中国标准时间记录。")
template_paragraph(61, "三、思考与实践")
subheading("1．修改脚本，在输出结果前询问文件名")
paragraph("在sum.sh加入--choose-output选项：先验证n并求和，再read读取输出文件名。sum_named.sh调用该分支；文件路径始终加双引号，因而带空格的文件名也能正确处理。")
picture("09-named-output.png", "图9  输入10及custom result.txt，生成的自选结果文件为55", width=17)
paragraph("完整包装脚本见src/sum_named.sh。写入失败返回1，不输出保存成功；该行为及空格文件名都已验证。")

page("实验2 Linux的基本操作（续）")
subheading("2．查阅资料，尝试编写Makefile")
paragraph("阅读提供的《扩展阅读——跟我一起写Makefile》，编写本目录的Makefile。默认目标all生成build/sum；build/sum依赖build/sum.o，后者依赖src/sum.c，分别演示编译和链接；clean、check声明为.PHONY。命令行前使用真正的TAB，$<表示第一个依赖，$@表示当前目标。")
picture("10-make-dependencies.png", "图10  首次构建、重复make、make -q及源码变化时的重建计划", width=17.2)
paragraph("make clean后首次make执行编译和链接；第二次make提示无需更新；make -q返回0，表示目标已是最新。make -n -W src/sum.c模拟源码更新，显示应重新编译和链接，但不实际改动源码时间。")
subheading("验证结果与实验记录")
picture("11-verification.png", "图11  自动验证的末段输出：All 30 checks passed.", width=17.2)
paragraph("30项检查覆盖C程序边界、脚本必测输入、错误日志追加、已有结果保留、前导零、数值范围、自选输出和写入失败，以及不同年份的4月16日筛选、4月17日排除、无匹配与文件合并。样例日期测试只在临时目录中进行，不修改根目录或报告截图中的系统时间。")
paragraph("依据：实验要求.docx第2—3页模板；上机作业.pptx第2—9页；Linux基本操作知识点提纲、Linux基础教程、命令行与shell脚本编程宝典中的重定向/管道/退出状态说明，以及Makefile扩展阅读。原始输出见logs，结果文件见evidence/home。")

# 页脚页码；保持原模板A4大小、页边距和楷体风格。
for section in doc.sections:
    section.footer_distance = Cm(0.6)
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    font(run, size=9)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.addnext(fld)

doc.core_properties.title = "计算机操作系统实验一、实验二报告"
doc.core_properties.subject = "Linux基本操作、shell脚本与Makefile"
doc.core_properties.author = "待填写"
doc.core_properties.last_modified_by = "待填写"
doc.core_properties.comments = "按课程DOCX第2、3页模板编写；插图为实际实验窗口截图。"
# 防止模板网格把新增段落的行距向上取整，导致截图说明被推到单独一页。
for p in doc._element.xpath(".//w:p"):
    props = p.find(qn("w:pPr"))
    if props is None:
        props = OxmlElement("w:pPr")
        p.insert(0, props)
    snap = OxmlElement("w:snapToGrid")
    snap.set(qn("w:val"), "0")
    props.append(snap)
doc.save(OUTPUT)
(BASE / "logs/report-assets.json").write_text(json.dumps({
    "template": str(TEMPLATE.relative_to(BASE.parent)), "template_pages": [2, 3],
    "report": OUTPUT.name, "figures": figures, "list_line_counts": counts,
    "student_fields": "待填写"}, ensure_ascii=False, indent=2))
print(OUTPUT)
print(f"Embedded {len(figures)} actual screenshots.")
