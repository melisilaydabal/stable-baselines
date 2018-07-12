import tensorflow as tf
import gym

import baselines.common.tf_util as tf_util
from baselines.common.distributions import make_proba_dist_type
from baselines.ppo1.mlp_policy import BasePolicy


class CnnPolicy(BasePolicy):
    recurrent = False

    def __init__(self, name, ob_space, ac_space, kind='large', sess=None, reuse=False):
        super(CnnPolicy, self).__init__()
        self.reuse = reuse
        self.name = name
        self._init(ob_space, ac_space, kind)
        self.scope = tf.get_variable_scope().name
        self.sess = sess

    def _init(self, ob_space, ac_space, kind):
        assert isinstance(ob_space, gym.spaces.Box)

        self.pdtype = pdtype = make_proba_dist_type(ac_space)
        sequence_length = None

        ob = tf_util.get_placeholder(name="ob", dtype=tf.float32, shape=[sequence_length] + list(ob_space.shape))

        with tf.variable_scope(self.name, reuse=self.reuse):
            x = ob / 255.0
            if kind == 'small':  # from A3C paper
                x = tf.nn.relu(tf_util.conv2d(x, 16, "l1", [8, 8], [4, 4], pad="VALID"))
                x = tf.nn.relu(tf_util.conv2d(x, 32, "l2", [4, 4], [2, 2], pad="VALID"))
                x = tf_util.flattenallbut0(x)
                x = tf.nn.relu(tf.layers.dense(x, 256, name='lin', kernel_initializer=tf_util.normc_initializer(1.0)))
            elif kind == 'large':  # Nature DQN
                x = tf.nn.relu(tf_util.conv2d(x, 32, "l1", [8, 8], [4, 4], pad="VALID"))
                x = tf.nn.relu(tf_util.conv2d(x, 64, "l2", [4, 4], [2, 2], pad="VALID"))
                x = tf.nn.relu(tf_util.conv2d(x, 64, "l3", [3, 3], [1, 1], pad="VALID"))
                x = tf_util.flattenallbut0(x)
                x = tf.nn.relu(tf.layers.dense(x, 512, name='lin', kernel_initializer=tf_util.normc_initializer(1.0)))
            else:
                raise NotImplementedError

            logits = tf.layers.dense(x, pdtype.param_shape()[0], name='logits',
                                     kernel_initializer=tf_util.normc_initializer(0.01))

            self.pd = pdtype.probability_distribution_from_flat(logits)
            self.vpred = tf.layers.dense(x, 1, name='value', kernel_initializer=tf_util.normc_initializer(1.0))[:, 0]

        self.state_in = []
        self.state_out = []

        stochastic = tf.placeholder(dtype=tf.bool, shape=())
        ac = self.pd.sample()
        self._act = tf_util.function([stochastic, ob], [ac, self.vpred])
