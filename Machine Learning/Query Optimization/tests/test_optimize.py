import unittest

from qopt.optimize import Config, ConfigSpace, merge_param_train
from skopt.space import Categorical, Integer, Real


class TestOptimize(unittest.TestCase):

    def test_merge_param_train(self):
        self.assertDictEqual(merge_param_train([{}]), {})
        self.assertDictEqual(merge_param_train([
            {
                'key1': 'value1',
                'key2': 'value2',
            },
            {
                'key1': 'value1.1',
            }]), {
                'key1': 'value1.1',
                'key2': 'value2',
            })


class TestConfigSpace(unittest.TestCase):

    def test_parse(self):
        space = {
            'str_category': ['value1', 'value2'],
            'int_category': [0, 1, 2, 5, 10],
            'int_range_default': {
                'low': 0,
                'high': 10,
            },
            'float_range_default': {
                'low': 0.0,
                'high': 10.0,
            },
            'int_range_log2': {
                'low': 1,
                'high': 10,
                'distribution': 'log-uniform',
                'base': 2,
            },
            'float_range_log2': {
                'low': 1.0,
                'high': 10.0,
                'distribution': 'log-uniform',
                'base': 2,
            },
        }
        config = ConfigSpace.parse({
            'name': 'name',
            'default': {
                'key': 'value1',
            },
            'space': space
        })

        self.assertEqual(config.name, 'name')
        self.assertDictEqual(config.default, {'key': 'value1'})

        # space
        self.assertEqual(len(config.space), len(space.keys()))
        # kept things in order, easier to test
        self.assertListEqual(config.dimension_names(), list(space.keys()))

        self.assertEqual(config.space[0], Categorical(['value1', 'value2'], name='str_category'))
        self.assertEqual(config.space[1], Categorical([0, 1, 2, 5, 10], transform='identity', name='int_category'))
        self.assertEqual(config.space[2], Integer(low=0, high=10, name='int_range_default'))
        self.assertEqual(config.space[3], Real(low=0.0, high=10.0, name='float_range_default'))
        self.assertEqual(config.space[4], Integer(low=1, high=10, prior='log-uniform', base=2, name='int_range_log2'))
        self.assertEqual(config.space[5], Real(low=1.0, high=10.0, prior='log-uniform', base=2, name='float_range_log2'))

    def test_select_method__provided(self):
        cs = ConfigSpace('name', {}, 'grid', None, [Categorical(['one', 'two'])])
        self.assertEqual(cs.select_method(), 'grid')

    def test_select_method__auto_mixed_dims(self):
        cs = ConfigSpace('name', {}, 'auto', 10, [Categorical(['one', 'two']), Integer(0, 1)])
        self.assertEqual(cs.select_method(), 'bayesian')

    def test_select_method__auto_low_dimensionality(self):
        # dimensionality = 2 < 10
        cs = ConfigSpace('name', {}, 'auto', 10, [Categorical(['one', 'two'])])
        self.assertEqual(cs.select_method(), 'grid')

        # dimensionality = 4 < 10
        cs = ConfigSpace('name', {}, 'auto', 10, [Categorical(['one', 'two']), Categorical(['three', 'four'])])
        self.assertEqual(cs.select_method(), 'grid')

        # dimensionality = 6 == 6
        cs = ConfigSpace('name', {}, 'auto', 6, [Categorical(['one', 'two']), Categorical(['three', 'four', 'five'])])
        self.assertEqual(cs.select_method(), 'grid')

    def test_select_method__auto_high_dimensionality(self):
        # dimensionality = 6 > 5
        cs = ConfigSpace('name', {}, 'auto', 5, [Categorical(['one', 'two']), Categorical(['three', 'four', 'five'])])
        self.assertEqual(cs.select_method(), 'bayesian')


class TestConfig(unittest.TestCase):

    def test_parse(self):
        json_config = {
            'default': {
                'key1': 'default1',
                'key2': 'default2',
            },
            'spaces': [
                {
                    'name': 'name1',
                    'default': {},
                    'space': {
                        'key1': ['value1', 'value2'],
                    },
                },
                {
                    'name': 'name2',
                    'default': {},
                    'space': {
                        'key1': ['value1', 'value2'],
                    },
                },
            ]
        }

        config = Config.parse(json_config)
        self.assertDictEqual(config.default, json_config['default'])

        # spaces
        self.assertEqual(len(config.spaces), len(json_config['spaces']))
        # kept things in order, this is essential
        self.assertListEqual(
            [space.name for space in config.spaces],
            [space['name'] for space in json_config['spaces']])
