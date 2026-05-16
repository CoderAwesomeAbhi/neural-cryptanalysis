from core import generate_sequence, find_trajectory_period

for seed in [0, 1, 42, 123, 999]:
    seq = generate_sequence(125, True, N=20000, burn=300, seed=seed)
    T = find_trajectory_period(seq, max_T=10000)
    print(f'seed={seed}: T={T}')
