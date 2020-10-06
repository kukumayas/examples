from functools import reduce
from skopt.space import Categorical, Integer, Real


class ConfigSpace:
    DEFAULT_METHOD = 'auto'
    DEFAULT_NUM_ITERATIONS = 30

    __DEFAULT_BASE = 10
    __DEFAULT_DISTRIBUTION = 'uniform'
    __METHODS = {'auto', 'grid', 'bayesian', None}
    __RANGE_FIELDS = {'low', 'high', 'distribution', 'base'}

    def __init__(self, name, default, method, num_iterations, space):
        assert name, "Name is required"
        assert method in ConfigSpace.__METHODS, f"Unsupported method: {method}, must be one of {ConfigSpace.__METHODS}"
        assert space, "Space is required"
        assert not (method == 'grid' and num_iterations), f"Number of iterations is not supported for grid search"

        self.name = name
        self.default = default or {}
        self.method = method or ConfigSpace.DEFAULT_METHOD
        self.num_iterations = num_iterations or ConfigSpace.DEFAULT_NUM_ITERATIONS
        self.space = space

    def dimension_names(self):
        return [dim.name for dim in self.space]

    def select_method(self):
        """Select method if it's auto, otherwise use the provided method."""

        def all_dimensions_are_categorical():
            return all([isinstance(dim, Categorical) for dim in self.space])

        def dimensionality():
            sizes = [len(dim.categories) for dim in self.space]
            return reduce(lambda x, y: x*y, sizes)

        if self.method != 'auto':
            # if a specific method was already chosen, use it
            return self.method
        elif not all_dimensions_are_categorical():
            # we can only do a grid search if all the dimensions are categorical
            return 'bayesian'
        elif dimensionality() <= self.num_iterations:
            # do a grid search only when the dimensionality is <= num iterations
            return 'grid'
        else:
            # default to bayesian as it's the most flexible option
            return 'bayesian'

    @staticmethod
    def __parse_space(space):
        """Parse a set of dimensions (space)."""
        assert isinstance(space, dict), "Space should be a dict of simple key-value pairs"

        def parse_dimension(name, values):
            """Parse a single dimension from JSON into an {{skopt.Dimension}}"""

            def convert_to_categorical_dimension():
                # discrete, but what kind?
                if isinstance(values[0], int):
                    return Categorical(values, transform='identity', name=name)
                elif isinstance(values[0], str):
                    return Categorical(values, transform='onehot', name=name)
                else:
                    raise ValueError("Discrete values can only be int or string.")

            def convert_to_numerical_dimension():
                if 'distribution' in values:
                    prior = values['distribution']
                else:
                    prior = ConfigSpace.__DEFAULT_DISTRIBUTION

                if 'base' in values:
                    base = values['base']
                else:
                    base = ConfigSpace.__DEFAULT_BASE

                # range, but what kind?
                if isinstance(values['low'], int):
                    return Integer(values['low'], values['high'], prior=prior, base=base, name=name)
                elif isinstance(values['low'], float):
                    return Real(values['low'], values['high'], prior=prior, base=base, name=name)
                else:
                    raise ValueError("Range values can only be int or float.")

            if isinstance(values, list):
                return convert_to_categorical_dimension()
            elif isinstance(values, dict) and set(values.keys()).issubset(ConfigSpace.__RANGE_FIELDS):
                return convert_to_numerical_dimension()
            else:
                raise ValueError(
                    f"Parameter config must be either a list of discrete values or a dictionary with field " +
                    "{RANGE_FIELDS}: {values}")

        return [parse_dimension(name, values) for name, values in space.items()]

    @staticmethod
    def parse(config):
        """Parse a space config from JSON into a concrete {{ConfigSpace}}."""
        assert 'name' in config, "Name is required in a space configuration"
        assert 'space' in config, "Space is required in a space configuration"

        return ConfigSpace(
            name=config['name'],
            default=config.get('default'),
            method=config.get('method'),
            num_iterations=config.get('num_iterations'),
            space=ConfigSpace.__parse_space(config['space']))


class Config:
    def __init__(self, default, spaces):
        self.default = default
        self.spaces = spaces

    @staticmethod
    def parse(config):
        """Parse a config from JSON into a concrete {{Config}} with nested {{ConfigSpace}}s."""
        assert isinstance(config['default'], dict), "Default params should be a dict of simple key-value pairs"
        assert isinstance(config['spaces'], list), "Spaces should be a list of dimensions"
        return Config(
            default=config['default'],
            spaces=[ConfigSpace.parse(space) for space in config['spaces']])


def merge_param_train(param_train):
    """
    Build a complete parameter set based on default, previously found parameters
    and any parameters to try. This assumes that the default parameters contain
    the superset of parameters and all subsequent parameters are a subset of the
    default parameter set.
    """

    assert isinstance(param_train, list), f"param_train needs to be a list of dicts, got {type(param_train)}={param_train}"
    for params in param_train:
        assert isinstance(params, dict), f"params needs to be a list of dicts, got {type(params)}={params}"
    assert len(param_train) >= 1, f"param_train must contain at least one dict"

    def validate_param_subset():
        all_keys = [set(p.keys()) for p in param_train]
        first = all_keys[0]
        for keys in all_keys[1::]:
            assert keys.issubset(first), \
                f"Parameters must be a subset of the default parameters: {keys}, default_params={first}"

    validate_param_subset()

    # merge copies of all the dicts from left to right
    merged = {}
    for params in param_train:
        merged.update(params)
    return merged
