from collections import namedtuple, OrderedDict

RatingBreakdown = namedtuple('RatingBreakdown', ['one', 'two', 'three', 'four', 'five'])


class Model(object):
    """
    Base class for objects corresponding to objects in the Q guide.
    """
    def __init__(self, **kwargs):
        raise NotImplementedError

    def validate(self):
        """
        Ensure that all fields are filled out and have correct types.
        Raises an AssertionError if it fails
        """
        raise NotImplementedError

    def to_json_dict(self):
        """
        Turns the object into a dictionary that can be serialised into JSON.
        Most objects use OrderedDicts in order to make the resultant JSON more
        readable.
        """
        raise NotImplementedError


class Course(object):
    """
    Object representing a course taught in a specific term.
    """
    def __init__(self, **kwargs):
        self.course_id = kwargs.get('course_id')
        self.department = kwargs.get('department')
        self.course_code = kwargs.get('course_code')
        self.course_name = kwargs.get('course_name')
        self.term = kwargs.get('term')
        self.year = kwargs.get('year')
        self.enrollment = kwargs.get('enrollment')
        self.evaluations = kwargs.get('evaluations')
        self.ratings = kwargs.get('ratings')
        self.reasons = kwargs.get('reasons')
        self.instructors = kwargs.get('instructors')
        self.questions = kwargs.get('questions')

    def validate(self):
        assert isinstance(self.course_id, int)
        assert isinstance(self.department, str)
        assert isinstance(self.course_code, str)
        assert isinstance(self.course_name, str)
        assert isinstance(self.term, int)
        assert isinstance(self.year, int)
        assert isinstance(self.enrollment, int)
        assert isinstance(self.evaluations, int)
        assert isinstance(self.ratings, list)
        assert isinstance(self.reasons, Reasons)
        assert isinstance(self.instructors, list)
        assert isinstance(self.questions, list)

        self.reasons.validate()

        for r in self.ratings:
            assert isinstance(r, Rating)
            r.validate()

        for i in self.instructors:
            assert isinstance(i, Instructor)
            i.validate()

        for q in self.questions:
            assert isinstance(q, Question)
            q.validate()

    def to_json_dict(self):
        self.validate()
        return OrderedDict([
            ('course_id', self.course_id),
            ('department', self.department),
            ('course_code', self.course_code),
            ('course_name', self.course_name),
            ('term', self.term),
            ('year', self.year),
            ('enrollment', self.enrollment),
            ('evaluations', self.evaluations),
            ('ratings', [r.to_json_dict() for r in self.ratings]),
            ('reasons', self.reasons.to_json_dict()),
            ('instructors', [i.to_json_dict() for i in self.instructors]),
            ('questions', [q.to_json_dict() for q in self.questions])
        ])


class Rating(object):
    """
    Ther rating for a particluar category (e.g. 'difficulty') for a particular
    Course
    """
    def __init__(self, **kwargs):
        self.category = kwargs.get('category')
        self.breakdown = kwargs.get('breakdown')

    def validate(self):
        assert isinstance(self.category, str)
        try:
            assert isinstance(self.breakdown, RatingBreakdown)
        except AssertionError:
            assert isinstance(self.breakdown, tuple)
            assert len(tuple) == 5
            self.breakdown = RatingBreakdown(*self.breakdown)

        for elt in self.breakdown:
            assert isinstance(elt, int)

    def to_json_dict(self):
        return OrderedDict([
            ('category', self.category),
            ('breakdown', self.breakdown)
        ])


class Reasons(object):
    """
    Reasons why students took a particular course (i.e. gened, elective, etc.)
    """
    def __init__(self, **kwargs):
        self.total_responses = kwargs.get('total_responses')
        self.breakdown = kwargs.get('breakdown')

    def validate(self):
        assert isinstance(self.total_responses, int)
        assert isinstance(self.breakdown, dict)

        expected_keys_1 = set((
            'Elective',
            'Concentration or Department Requirement',
            'Secondary Field or Language Citation Requirement',
            'Undergraduate Core or General Education Requirement',
            'Expository Writing Requirement',
            'Foreign Language Requirement',
            'Pre-Med Requirement'))

        # Set of allowed reasons changed in ~2007
        expected_keys_2 = set((
            'Elective',
            'Concentration/Program Requirement',
            'Undergraduate Core Requirement',
            'Pre-Med Requirement'
        ))

        actual_keys = set(self.breakdown.keys())
        assert actual_keys == expected_keys_1 or actual_keys == expected_keys_2

        for v in self.breakdown.values():
            assert isinstance(v, int)

    def to_json_dict(self):
        return OrderedDict([
            ('total_responses', self.total_responses),
            ('breakdown', self.breakdown)
        ])


class Instructor(object):
    """
    Ratings for a particular instructor teaching a particular Course in a
    particular semester
    """
    def __init__(self, **kwargs):
        self.instructor_id = kwargs.get('instructor_id')
        self.instructor_role = kwargs.get('instructor_role')
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.ratings = kwargs.get('ratings')

    def validate(self):
        assert isinstance(self.instructor_id, str)
        assert isinstance(self.instructor_role, str)
        assert isinstance(self.first_name, str)
        assert isinstance(self.last_name, str)
        assert isinstance(self.ratings, list)

        for r in self.ratings:
            assert isinstance(r, Rating)
            r.validate()

    def to_json_dict(self):
        return OrderedDict([
            ('instructor_id', self.instructor_id),
            ('instructor_role', self.instructor_role),
            ('first_name', self.first_name),
            ('last_name', self.last_name),
            ('ratings', [r.to_json_dict() for r in self.ratings])
        ])


class Question(object):
    """
    Question (with student responses) about a particluar course. Most common
    question asked is "What would you tell future students about this course?"
    """
    def __init__(self, **kwargs):
        self.question = kwargs.get('question')
        self.responses = kwargs.get('responses')

    def validate(self):
        assert isinstance(self.question, str)
        assert isinstance(self.responses, list)

        for r in self.responses:
            assert isinstance(r, str)

    def to_json_dict(self):
        return OrderedDict([
            ('question', self.question),
            ('responses', self.responses)
        ])
