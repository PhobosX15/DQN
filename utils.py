import os
import numpy as np
import torch
import gym
from Param import *
import matplotlib.pyplot as plt
from IPython.display import clear_output

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def plot_stats(frame_idx, rewards, losses):
    clear_output(True)
    plt.figure(figsize=(20,5))
    plt.subplot(131)
    plt.title(f'Total frames {frame_idx}. Avg reward over last 10 episodes: {np.mean(rewards[-10:])}')
    plt.plot(rewards)
    plt.subplot(132)
    plt.title('loss')
    plt.plot(losses)
    plt.show()


def compute_loss(model, replay_buffer, batch_size, gamma):
    state, action, reward, next_state, done = replay_buffer.sample(batch_size)

    state = torch.FloatTensor(np.float32(state)).to(device)
    next_state = torch.FloatTensor(np.float32(next_state)).to(device)
    action = torch.LongTensor(action).to(device)
    reward = torch.FloatTensor(reward).to(device)
    done = torch.FloatTensor(done).to(device)

    q_values_old = model(state)
    q_values_new = model(next_state)

    q_value_old = q_values_old.gather(1, action.unsqueeze(1)).squeeze(1)
    q_value_new = q_values_new.max(1)[0]
    expected_q_value = reward + gamma * q_value_new * (1 - done)

    loss = (q_value_old - expected_q_value.data).pow(2).mean()

    return loss

def train(env, model, optimizer, replay_buffer, device=device):
    steps_done = 0
    episode_rewards = []
    losses = []
    model.train()
    for episode in range(EPISODES):
        state = env.reset()
        episode_reward = 0.0
        while True:
            epsilon = EPS_END + (EPS_START - EPS_END) * np.exp(- steps_done / EPS_DECAY)
            action = model.act(state, epsilon, device)
            steps_done += 1

            next_state, reward, done, _ = env.step(action)
            replay_buffer.push(state, action, reward, next_state, done)

            state = next_state
            episode_reward += reward

            if len(replay_buffer) > INITIAL_MEMORY:
                loss = compute_loss(model, replay_buffer, BATCH_SIZE, GAMMA)

                # Optimization step
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                losses.append(loss.item())

            if steps_done % 10000 == 0:
                plot_stats(steps_done, episode_rewards, losses)

            if done:
                episode_rewards.append(episode_reward)
                break
        if (episode+1) % 100 == 0 or episode+1 == 10:
            path = os.path.join(MODEL_SAVE_PATH, f"{env.spec.id}_episode_{episode+1}.pth")
            print(f"Saving weights at Episode {episode+1} ...")
            torch.save(model.state_dict(), path)
    env.close()


def test(env, model, episodes, render=True, device=device, context=""):
    env = gym.wrappers.Monitor(env, VIDEO_SAVE_PATH + f'dqn_pong_video_{context}')
    model.eval()
    for episode in range(episodes):
        state = env.reset()
        episode_reward = 0.0
        while True:
            action = model.act(state, 0, device)
            next_state, reward, done, _ = env.step(action)

            if render:
                env.render()
                time.sleep(0.02)

            episode_reward += reward
            state = next_state

            if done:
                print(f"Finished Episode {episode+1} with reward {episode_reward}")
                break

    env.close()
