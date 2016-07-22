import json
from multiprocessing import Pool
import os
import sys
import traceback

from models import Course, Instructor, Rating, RatingBreakdown, Reasons, Question
from request_maker import RequestMaker


def scrape_term(requester, output_dir, year, term):
    """
    Scrapes data for an entire term of courses
    """
    url_base = '/course_evaluation_reports/fas/list'
    url = '{base}?yearterm={year}_{term}'.format(base=url_base,
                                                 year=year,
                                                 term=term)
    soup = requester.make_request(url)
    categories = [c.attrs['title_abbrev'] for c in soup.select('.course-block-title')]

    for category in categories:
        # Scrape each category in the term
        scrape_category(requester, output_dir, year, term, category)


def scrape_category(original_requester, output_dir, year, term, category):
    """
    Scrape a category within a term (i.e. Anthropology, Engineering)
    """
    try:
        requester = RequestMaker.copy(original_requester)

        category_url_fmt = ('/course_evaluation_reports/fas/guide_dept?'
                            'dept={category}&term={term}&year={year}')
        courses = requester.make_request(category_url_fmt.format(
            category=category, term=term, year=year))
        course_links = [c.attrs['href'] for c in courses.select('.course a')]
        course_ids = [int(link.split('=')[1]) for link in course_links]

        for cid in course_ids:
            # Scrape data from each course
            scrape_course(requester, output_dir, cid, year, term)
    except:
        traceback.print_exc()
        raise


def scrape_course(requester, output_dir, course_id, year, term):
    """
    Scrapes all data for a particluar course, including ratings, comments,
    and instructor ratings.
    """
    # This course is weird. Let's skip it.
    if course_id in (44050,):
        print('There is some weird shit going on with course {}'.format(course_id))
        return

    c = Course(course_id=course_id, year=year, term=term)
    base_url = '/course_evaluation_reports/fas/course_summary.html'
    url = '{base_url}?course_id={course_id}'.format(base_url=base_url,
                                                    course_id=course_id)

    soup = requester.make_request(url)

    # Get course name, department, enrollment, etc.
    if soup.h1 is None:
        print('No data for course {}'.format(course_id))
        return

    title = soup.h1.text
    colon_loc = title.find(':')
    c.department, c.course_code = title[:colon_loc].split()
    c.course_name = title[colon_loc + 2:]

    stats = soup.select('#summaryStats')[0].text.split()
    c.enrollment = int(stats[1])
    c.evaluations = int(stats[3])

    # Get course ratings
    graph_reports = soup.select('.graphReport')
    if not graph_reports:
        print('No data for course {}'.format(course_id))
        return

    c.ratings = []
    for graph_report in graph_reports[:-1]:
        c.ratings += scrape_ratings(graph_report)

    # Get reasons for why people signed up
    c.reasons = scrape_reasons(graph_reports[-1])

    c.instructors = scrape_instuctors(requester, course_id)
    c.questions = scrape_questions(requester, course_id)

    c.validate()
    filename = os.path.join(output_dir, '{}.json'.format(c.course_id))
    with open(filename, 'w') as f:
        json.dump(c.to_json_dict(), f, indent=3)


def scrape_ratings(graph_report):
    """
    Scrape reasons data from a ".graphReport" section of the page. These objects
    are weirdly inconsistent accross pages, hence all the "if" statements.
    """
    ratings = []
    graphs = graph_report.select('tr')[1:]
    for graph in graphs:
        tds = graph.select('td')
        if len(tds) == 1: continue

        category = tds[0].strong.text
        breakdown = RatingBreakdown(0, 0, 0, 0, 0)

        if tds[1].img is not None:
            dashes = tds[1].img.attrs['src'].replace('../histobar-', '').replace('.png', '')
            breakdown = RatingBreakdown(*map(int, dashes.split('-')))

        ratings.append(Rating(category=category, breakdown=breakdown))

    return ratings


def scrape_reasons(reasons_graph):
    """
    Scrapes reasons from the graph showing reasons why students take the class
    """
    total = 0
    breakdown = {}
    for row in reasons_graph.select('tr')[1:]:
        tds = row.select('td')
        category = tds[0].text
        dashes = tds[1].img.attrs['src'].replace('../barPercentage-', '').replace('.png', '')
        n, total, _ = map(int, dashes.split('-'))
        breakdown[category] = n

    return Reasons(total_responses=total, breakdown=breakdown)


def scrape_instuctors(requester, course_id, instr_id=None):
    """
    Scrape instructor data
    """
    instr = Instructor()
    url = '/course_evaluation_reports/fas/inst-tf_summary.html?course_id={}'.format(course_id)
    if instr_id is not None:
        url += '&current_instructor_or_tf_huid_param={}'.format(instr_id)

    soup = requester.make_request(url)
    select = soup.select('select[name="current_instructor_or_tf_huid_param"]')[0]

    if not select.select('option'):
        print('No instructors found for this course')
        return []

    option = select.select('option[selected="selected"]')[0]
    id_role = option.attrs['value']
    instr.instructor_id, instr.instructor_role = id_role.split(':')
    instr.last_name, instr.first_name = map(str.strip, option.text.split(','))

    graph_reports = soup.select('.graphReport')
    if not graph_reports:
        instr.ratings = []
        print('No ratings for instructor {} {}'.format(instr.first_name,
                                                       instr.last_name))
    else:
        if len(graph_reports) != 1:
            print('More than one graph report found')
        instr.ratings = scrape_ratings(graph_reports[0])
    instr_lst = [instr]

    # Don't want recursion more than one level deep
    if instr_id is None:
        for option in select.select('option')[1:]:
            iid = option.attrs['value']
            instr_lst += scrape_instuctors(requester, course_id, iid)

    return instr_lst


def scrape_questions(requester, course_id):
    """
    Scrape all the questions about the course along with student responses
    """
    questions = []
    base_url = '/course_evaluation_reports/fas/view_comments.html'
    all_questions_url = '{}?course_id={}'.format(base_url, course_id)

    all_soup = requester.make_request(all_questions_url)
    question_links = all_soup.select('#reportContent h3 a')
    for q_link in question_links:
        q = Question(question=q_link.text)
        q_url = '/course_evaluation_reports/fas/{}'.format(q_link.attrs['href'])
        q_soup = requester.make_request(q_url)
        q.responses = [r.text.strip() for r in q_soup.select('.response p')]

        questions.append(q)

    return questions


def main():
    # Load credentials
    username = ''
    password = ''
    with open('credentials.txt') as f:
        username, password = f.read().split()

    requester = RequestMaker(username, password)

    if not os.path.exists('output'):
        os.makedirs('output')

    # Output JSON files to new directory in order to avoid overwriting past runs
    existing_outputs = map(int, filter(str.isdigit, os.listdir('output')))
    new_output = 0 if not existing_outputs else max(existing_outputs) + 1
    output_dir = os.path.join('output', str(new_output))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    year_terms = [(2015, 1), (2014, 2), (2014, 1), (2013, 2), (2013, 1),
                  (2012, 2), (2012, 1), (2011, 2), (2011, 1), (2010, 2),
                  (2010, 1), (2009, 2), (2009, 1), (2008, 2), (2008, 1),
                  (2007, 2), (2007, 1), (2006, 2), (2006, 1)]

    # Most of the time is spent waiting for the Q Guide to send a response, so
    # parallelize with 5 processes
    args = [(requester, output_dir, year, term) for year, term in year_terms]
    p = Pool(5)
    p.map(_helper, args)


def _helper(t):
    (requester, output_dir, year, term) = t
    scrape_term(RequestMaker.copy(requester), output_dir, year, term)

if __name__ == '__main__':
    # Don't buffer stdout
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    main()
