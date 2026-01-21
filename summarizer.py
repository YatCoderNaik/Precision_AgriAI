import numpy as np

def summarize_vector(vector):
    """
    Performs Structural Analysis on a 64-dimensional latent embedding.
    Calculates statistical moments and derives heuristic Agri-Tokens.
    """
    if not vector or len(vector) < 64:
        return {
            "mean": 0, "variance": 0, "flux": 0, 
            "tokens": ["Incomplete Signal"],
            "summary_text": "Insufficient data for structural analysis."
        }

    v = np.array(vector)
    
    # 1. Statistical Moments
    mean_val = float(np.mean(v))
    var_val = float(np.var(v))
    
    # 2. Structural Flux (Heuristic: Early vs Late dimensions)
    # Early: 0-20, Late: 21-63
    early_mean = np.mean(v[:21])
    late_mean = np.mean(v[21:])
    flux_val = float(early_mean - late_mean)
    
    # 3. Derive Semantic Tokens (Based on documented rules)
    tokens = []
    
    # Mean Rules
    if mean_val > 0.05: tokens.append("Robust Signal Activation")
    elif mean_val < -0.05: tokens.append("Suppressed Latent Response")
    
    # Variance Rules
    if var_val < 0.005: tokens.append("Uniform Canopy Profile")
    elif var_val > 0.015: tokens.append("High Structural Heterogeneity")
    
    # Flux Rules
    if flux_val > 0.03: tokens.append("Early-Dimension Dominance")
    elif flux_val < -0.03: tokens.append("Late-Dimension Focus")
    
    if not tokens:
        tokens.append("Stable Structural Signature")

    # 4. Construct Human-Readable Summary
    summary = f"Statistical Profile: Mean={mean_val:.4f}, Var={var_val:.4f}. "
    summary += f"Structural Flux indicates {('Early' if flux_val > 0 else 'Late')}-dominant signal. "
    summary += f"Decoded Tokens: {', '.join(tokens)}."

    return {
        "mean": round(mean_val, 4),
        "variance": round(var_val, 4),
        "flux": round(flux_val, 4),
        "tokens": tokens,
        "summary_text": summary
    }

if __name__ == "__main__":
    # Test with dummy data
    test_v = [0.1]*21 + [-0.1]*43
    print(summarize_vector(test_v))
