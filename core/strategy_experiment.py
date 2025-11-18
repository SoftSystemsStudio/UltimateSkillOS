import random

class StrategyExperimenter:
    def __init__(self, strategies):
        self.strategies = strategies
        self.results = {s: [] for s in strategies}

    def try_alternative(self, query, agent, reward_fn):
        strategy = random.choice(self.strategies)
        agent.router.set_strategy(strategy)
        result = agent.execute(query)
        reward = reward_fn(result)
        self.results[strategy].append(reward)
        return strategy, reward

    def get_best_strategy(self):
        avg_rewards = {s: (sum(r)/len(r) if r else 0) for s, r in self.results.items()}
        return max(avg_rewards, key=avg_rewards.get)
