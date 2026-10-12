"""Helpers for the deep-learning-pytorch course.

Import in pre_code or tests as `from kits.deep_learning_pytorch import ...`.

- check_tensor(user, sol, name, ...): tensor-aware version of check_equal with shape/dtype feedback.
  (The harness's check_equal cannot compare multi-element torch tensors.)
- digits_split(): sklearn's 8x8 digits as (N, 1, 8, 8) float tensors in [0, 1], a fixed stratified split.
- shift(images, dx, dy): move a batch of images by whole pixels, filling with zeros (no wrap-around).
- shifted_copies(X, y): the four 1-pixel shifts of every image, stacked, for robustness tests.
"""

import torch


def _fmt_shape(t):
    return tuple(t.shape)


def check_tensor(user, sol, name, atol=1e-4, rtol=1e-4, expected=None, msg=None, check_dtype=False):
    """Fail with a helpful message unless user[name] is a tensor close to the solution's (or `expected`)."""
    if name not in user:
        raise AssertionError(msg or f"Did you define `{name}`? It does not exist yet.")
    got = user[name]
    want = sol[name] if expected is None else expected
    want = torch.as_tensor(want)
    if not isinstance(got, torch.Tensor):
        # Plain numbers are fine for scalar results (e.g. after .item()); anything else must be a tensor.
        if want.dim() == 0 and isinstance(got, (int, float)) and not isinstance(got, bool):
            got = torch.tensor(float(got))
        else:
            raise AssertionError(f"`{name}` should be a torch tensor, but it is a {type(got).__name__}.")
    if got.shape != want.shape:
        raise AssertionError(msg or f"`{name}` has shape {_fmt_shape(got)}, but it should have shape {_fmt_shape(want)}.")
    if check_dtype and got.dtype != want.dtype:
        raise AssertionError(msg or f"`{name}` has dtype {got.dtype}, but it should be {want.dtype}.")
    g = got.detach().to(torch.float64)
    w = want.detach().to(torch.float64)
    if not torch.allclose(g, w, atol=atol, rtol=rtol, equal_nan=True):
        raise AssertionError(msg or f"`{name}` has the right shape but the wrong values. Check how you computed it.")
    return True


def digits_split(test_size=0.25, seed=0):
    """Return X_train, X_test, y_train, y_test: images (N, 1, 8, 8) float32 in [0, 1], labels int64."""
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split

    d = load_digits()
    X = torch.tensor(d.images / 16.0, dtype=torch.float32).unsqueeze(1)
    y = torch.tensor(d.target, dtype=torch.int64)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)
    return Xtr, Xte, ytr, yte


def shift(images, dx, dy):
    """Shift (N, C, H, W) images right by dx and down by dy pixels (|dx|, |dy| <= 1), zero-filled."""
    import torch.nn.functional as F

    H, W = images.shape[-2:]
    padded = F.pad(images, (1, 1, 1, 1))
    return padded[..., 1 - dy : 1 - dy + H, 1 - dx : 1 - dx + W]


def shifted_copies(X, y):
    """Every image moved one pixel left, right, up and down: 4x as many images."""
    moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    return torch.cat([shift(X, dx, dy) for dx, dy in moves]), torch.cat([y for _ in moves])
