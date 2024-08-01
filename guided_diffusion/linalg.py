import torch


@torch.no_grad()
def conjugate_gradient(A, b, x=None, maxiter=1):
    if x is None:
        x = torch.zeros_like(b)
        r = b
    else:
        r = b - A(x)

    rr = torch.sum(r * r)
    p = r

    for _ in range(maxiter):
        Ap = A(p)
        pAp = torch.sum(p * Ap)
        alpha = rr / pAp
        x_ = x + alpha * p
        r_ = r - alpha * Ap
        rr_ = torch.sum(r_ * r_)
        beta = rr_ / rr
        p_ = r_ + beta * p

        x, r, rr, p = x_, r_, rr_, p_

    return x


def safe_normalize(x, threshold=1e-6):
    norm = torch.linalg.vector_norm(x)

    new_x = torch.where(
        norm > threshold,
        x / norm,
        torch.zeros_like(x),
    )

    return new_x, norm


def arnoldi(p, V, H, j):
    for i in range(j):
        H[i, j - 1] = torch.sum(p * V[i])
        p = p - H[i, j - 1] * V[i]
    new_p, norm = safe_normalize(p)
    H[j, j - 1] = norm
    return new_p


def cal_rotation(a, b):
    c = torch.sqrt(a * a + b * b)
    return a / c, -b / c


def apply_rotation(H, cs, ss, j):
    for i in range(j):
        tmp = cs[i] * H[i, j] - ss[i] * H[i + 1, j]
        H[i + 1, j] = cs[i] * H[i + 1, j] + ss[i] * H[i, j]
        H[i, j] = tmp
    cs[j], ss[j] = cal_rotation(H[j, j], H[j + 1, j])
    H[j, j] = cs[j] * H[j, j] - ss[j] * H[j + 1, j]
    H[j + 1, j] = 0
    return H, cs, ss


@torch.no_grad()
def gmres(A, b, x=None, maxiter=1):
    if x is None:
        x = torch.zeros_like(b)
        r = b
    else:
        r = b - A(x)

    new_v, norm = safe_normalize(r)

    beta = torch.zeros(maxiter + 1, device=b.device)
    beta[0] = norm

    V = []
    V.append(new_v)
    H = torch.zeros((maxiter + 1, maxiter + 1), device=b.device)
    cs = torch.zeros(maxiter, device=b.device)  # cosine values at each step
    ss = torch.zeros(maxiter, device=b.device)  # sine values at each step

    for i in range(maxiter):
        p = A(V[i])
        new_v = arnoldi(p, V, H, i + 1)  # Arnoldi iteration to get the i+1 th basis
        V.append(new_v)

        H, cs, ss = apply_rotation(H, cs, ss, i)
        beta[i + 1] = ss[i] * beta[i]
        beta[i] = cs[i] * beta[i]

    V = torch.stack(V[:-1], dim=-1)
    y = torch.linalg.solve_triangular(
        H[0 : i + 1, 0 : i + 1],
        beta[0 : i + 1].unsqueeze(-1),
        upper=True,
    ).squeeze(-1)

    sol = x + torch.einsum("...i,i", V, y)

    return sol
