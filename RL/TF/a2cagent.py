import gym
import tensorflow as tf
import numpy as np
import model

import tensorflow.keras.losses as kls
import tensorflow.keras.optimizers as ko

class A2CAgent:
    def __init__(self, model):
        # hyperparameters for loss terms
        self.params = {'value': 0.5, 'entropy': 0.0001, 'gamma': 0.99}
        self.model = model
        self.model.compile(optimizer=ko.RMSprop(lr=0.0007),
                            # define separate losses for policy logits and value estimate
                            loss=[self._logits_loss, self._value_loss])

    def test(self, env, render=True):
        obs, done, ep_reward = env.reset(), False, 0
        while not done:
            #print("\n", obs, "\n")
            hashed_obs = self.hash_obs(obs)
            #print(hashed_obs, "\n")
            action, _ = self.model.action_value(hashed_obs)
            obs, reward, done, _ = env.step(action)
            ep_reward += reward
            if render:
                env.render()
        return ep_reward

    def _value_loss(self, returns, value):
        # value loss is typically MSE between value estimates and returns
        return self.params['value']*kls.mean_squared_error(returns, value)

    def _logits_loss(self, acts_and_advs, logits):
        # a trick to input actions and advantages through same API
        actions, advantages = tf.split(acts_and_advs, 2, axis=-1)
        # sparse categorical CE loss obj that supports sample_weight arg on call()
        # from_logits argument ensures transformation into normalized probabilities
        weighted_sparse_ce = kls.SparseCategoricalCrossentropy(from_logits=True)
        # policy loss is defined by policy gradients, weighted by advantages
        # note: we only calculate the loss on the actions we've actually taken
        actions = tf.cast(actions, tf.int32)
        policy_loss = weighted_sparse_ce(actions, logits, sample_weight=advantages)
        # entropy loss can be calculated via CE over itself
        entropy_loss = kls.categorical_crossentropy(logits, logits, from_logits=True)
        # here signs are flipped because optimizer minimizes
        return policy_loss - self.params['entropy']*entropy_loss

    def train(self, env, batch_sz=32, updates=200):
        # storage helpers for a single batch of data
        actions = np.empty((batch_sz,), dtype=np.int32)
        rewards, dones, values = np.empty((3, batch_sz))
        observations = np.empty((batch_sz,) + env.observation_space.shape)
        # training loop: collect samples, send to optimizer, repeat updates times
        ep_rews = [0.0]
        next_obs = env.reset()
        for update in range(updates):
            print(update)
            for step in range(batch_sz):
                observations[step] = next_obs.copy()
                actions[step], values[step] = self.model.action_value(next_obs[None, :])
                next_obs, rewards[step], dones[step], _ = env.step(actions[step])

                ep_rews[-1] += rewards[step]
                if dones[step]:
                    ep_rews.append(0.0)
                    next_obs = env.reset()

            _, next_value = self.model.action_value(next_obs[None, :])
            returns, advs = self._returns_advantages(rewards, dones, values, next_value)
            # a trick to input actions and advantages through same API
            acts_and_advs = np.concatenate([actions[:, None], advs[:, None]], axis=-1)
            # performs a full training step on the collected batch
            # note: no need to mess around with gradients, Keras API handles it
            losses = self.model.train_on_batch(observations, [acts_and_advs, returns])
        return ep_rews

    def _returns_advantages(self, rewards, dones, values, next_value):
        # next_value is the bootstrap value estimate of a future state (the critic)
        returns = np.append(np.zeros_like(rewards), next_value, axis=-1)
        # returns are calculated as discounted sum of future rewards
        for t in reversed(range(rewards.shape[0])):
            returns[t] = rewards[t] + self.params['gamma'] * returns[t+1] * (1-dones[t])
        returns = returns[:-1]
        # advantages are returns - baseline, value estimates in our case
        advantages = returns - values
        return returns, advantages

    def hash_obs(self, obs):
        if type(obs) == dict:
            hashed_obs = self.hash_dict(obs)
        elif type(obs) == list:
            hashed_obs = self.hash_list(obs)
        else: # for CartPole
            hashed_obs = np.array([])
            for a in obs:
                hashed_obs = np.append(hashed_obs, hash(a))
            #hashed_obs = obs
        print("\nlength: ", len(hashed_obs))        
        hashed_obs = hashed_obs[None, :]    
        return hashed_obs

    def hash_list(self, raw):
        hashed_list = np.array([])
        for a in raw:
            if type(a) == list:
                hashed_list = np.append(hashed_list, self.hash_list(a))
            if type(a) == dict:
                hashed_list = np.append(hashed_list, self.hash_dict(a))
            else:
                hashed_list = np.append(hashed_list, hash(a))
        return hashed_list

    def hash_dict(self, raw):
        hashed_dict = np.array([])
        for a in raw:
            if type(raw[a]) == list:
                hashed_dict = np.append(hashed_dict, self.hash_list(raw[a]))
            elif type(raw[a]) == dict:
                hashed_dict = np.append(hashed_dict, self.hash_dict(raw[a]))
            else:
                hashed_dict = np.append(hashed_dict, hash(raw[a]))
        return hashed_dict
