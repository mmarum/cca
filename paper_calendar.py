import calendar

def make_cal(db, month, year):
    this_calendar = calendar.HTMLCalendar(calendar.SUNDAY)
    combined_cals = ""

    month_range = []
    c = 0
    m = month
    for i in range(4):
        if m+c > 12:
            m = 1
            c = 0
        month_range.append(m+c)
        c += 1

    prev_month = 0

    for m in month_range:

        if prev_month == 12:
            year += 1

        if m == 12:
            next_month = 1
        else:
            next_month = m + 1

        if m == 1:
            prev_month = 12
        else:
            prev_month = m - 1

        #print(f"month: {m}")
        #print(f"year: {year}")

        one_month_cal = this_calendar.formatmonth(year, m)
        one_month_cal = one_month_cal.replace("&nbsp;"," ")
        prev_link = f"<div id='prev_link'><a href='#' onclick='showMonth({prev_month}); return false;'>&#171; Prev</a></div>\n"
        next_link = f"<div id='next_link'><a href='#' onclick='showMonth({next_month}); return false;'>Next &#187;</a></div>\n"
        one_month_cal = f"<div id='month{m}'>\n{one_month_cal}\n{prev_link} {next_link}\n</div>\n"
        c = db.cursor()

        c.execute(f"SELECT edatetime FROM events WHERE MONTH(edatetime) = {m} AND YEAR(edatetime) = {year} AND edatetime >= CURTIME() and (tags <> 'invisible' or tags is null)")
        allrows = c.fetchall()

        #print(allrows)

        c.close()
        zm = "0"+str(m) if len(str(m)) == 1 else m
        for d in allrows:
            day = str(d[0])
            day = day.split(' ')[0].split('-')[2].lstrip('0')
            zd = "0"+str(day) if len(str(day)) == 1 else day
            one_month_cal = one_month_cal.replace(f'">{day}<', f' event"><a href="/calendar.html#{year}-{zm}-{zd}" >{day}</a><')
        combined_cals += one_month_cal

        #print(combined_cals)

        prev_month = m

    return combined_cals


def make_list(db):
    c = db.cursor()
    c.execute(f"select eid, edatetime, title from events where edatetime > now() and (tags <> 'invisible' or tags is null) limit 7")
    allrows = c.fetchall()
    c.close()
    event_list_string = ""
    for d in allrows:
        eid = d[0]
        edatetime = d[1]
        date_string = edatetime.strftime("%b %d %Y")
        title = d[2]
        event_list_string += f'<div class="event_item">{date_string} <a href="/event/{eid}.html">{title}</a></div>\n'
    return event_list_string

