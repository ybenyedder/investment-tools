import numpy as np

def sinkhorn_knopp(a, b, C, epsilon, max_iter=1000, tol=1e-9):
    """
    Computes the Entropic Optimal Transport plan using the Sinkhorn algorithm.
    
    :param a: Source distribution (1D array of probabilities summing to 1)
    :param b: Target distribution (1D array of probabilities summing to 1)
    :param C: Cost matrix where C[i, j] is the cost of moving from a[i] to b[j]
    :param epsilon: Entropic regularization parameter (higher = more fuzzy/stochastic)
    :param max_iter: Maximum iterations
    :param tol: Convergence tolerance
    :return: Transport plan matrix P
    """
    # Compute the Gibbs kernel
    K = np.exp(-C / epsilon)
    
    # Initialize scaling vectors
    u = np.ones_like(a)
    v = np.ones_like(b)
    
    for i in range(max_iter):
        u_prev = u.copy()
        
        # Sinkhorn updates
        v = b / np.dot(K.T, u)
        u = a / np.dot(K, v)
        
        # Check for convergence
        if np.max(np.abs(u - u_prev)) < tol:
            print(f"Converged at iteration {i}")
            break
            
    # Compute the final transport plan
    P = np.diag(u) @ K @ np.diag(v)
    return P

def main():
    print("=== Entropic Optimal Transport (Sinkhorn) Demo ===\n")
    
    # 1. Define two simple 1D distributions (e.g., initial and final stock states)
    # Let's say we have 3 possible states for distribution A, and 3 for distribution B
    a = np.array([0.2, 0.5, 0.3]) # Source probabilities
    b = np.array([0.4, 0.4, 0.2]) # Target probabilities
    
    # 2. Define a cost matrix (e.g., squared distance between states)
    # States: x = [1, 2, 3], y = [1, 2, 3]
    x = np.array([1, 2, 3])
    y = np.array([1, 2, 3])
    
    C = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            C[i, j] = (x[i] - y[j])**2
            
    print("Source Distribution (a):", a)
    print("Target Distribution (b):", b)
    print("\nCost Matrix (C):\n", C)
    
    # 3. Compute Transport Plans with different Entropic parameters (epsilon)
    epsilons = [0.01, 1.0, 10.0]
    
    for eps in epsilons:
        print(f"\n--- Epsilon (Entropy) = {eps} ---")
        try:
            P = sinkhorn_knopp(a, b, C, epsilon=eps)
            print("Optimal Transport Plan (P):")
            print(np.round(P, 4))
            
            # Verify constraints
            print("Row sums (should match 'a'):", np.round(np.sum(P, axis=1), 4))
            print("Col sums (should match 'b'):", np.round(np.sum(P, axis=0), 4))
        except Warning as w:
            print("Numerical instability (common with very low epsilon without log-domain stabilization)")

if __name__ == "__main__":
    main()
