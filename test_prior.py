import warnings
import numpy as np
from scipy.integrate import quad, dblquad, tplquad

import prior
from utils import timer


@timer
def test_NIW(full=False):
    mu_0 = np.r_[0.2, 0.1]
    kappa_0 = 2.0
    Lam_0 = np.eye(2)+0.1
    nu_0 = 3

    # Create a Normal-Inverse-Wishart prior.
    niw = prior.NIW(mu_0, kappa_0, Lam_0, nu_0)

    # Check that we can draw samples from niw.
    niw.sample()
    niw.sample(size=10)

    # Check that we can evaluate a likelihood given data.
    theta = (np.r_[1., 1.], np.eye(2)+0.12)
    D = np.array([[0.1, 0.2], [0.2, 0.3], [0.1, 0.2], [0.4, 0.3]])
    niw.likelihood(*theta, D=D)

    # Evaluate prior
    niw(*theta)

    # Check prior predictive density
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        r = dblquad(lambda x, y: niw.pred([x, y]), -np.inf, np.inf,
                    lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5,
                                   "NIW prior predictive density does not integrate to 1.0")

    # Check posterior predictive density
    r = dblquad(lambda x, y: niw.post(D).pred([x, y]), -np.inf, np.inf,
                lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5,
                                   "NIW posterior predictive density does not integrate to 1.0")

    # Check that the likelihood of a single point in 2 dimensions integrates to 1.
    r = dblquad(lambda x, y: niw.like1(mu=np.r_[1.2, 1.1], Sig=np.eye(2)+0.12, x=[x, y]),
                -np.inf, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIW likelihood does not integrate to 1.0")

    if __name__ == "__main__" and full:
        # Check that likelihood of a single point in 3 dimensions integrates to 1.
        niw3 = prior.NIW([1]*3, 2.0, np.eye(3), 3)
        r = tplquad(lambda x, y, z: niw3.like1(np.r_[0.1, 0.2, 0.3], np.eye(3)+0.1, [x, y, z]),
                    -np.inf, np.inf,
                    lambda x: -np.inf, lambda x: np.inf,
                    lambda x, y: -np.inf, lambda x, y: np.inf)
        np.testing.assert_almost_equal(r[0], 1.0, 8,
                                       "NIW likelihood does not integrate to 1.0")

    # Check that posterior is proportional to prior * likelihood
    D = np.array([[0.1, 0.2], [0.2, 0.3], [0.1, 0.2], [0.4, 0.3]])
    mus = [np.r_[2.1, 1.1], np.r_[0.9, 1.2], np.r_[0.9, 1.1]]
    Sigs = [np.eye(2)*1.5, np.eye(2)*0.7, np.array([[1.1, -0.1], [-0.1, 1.2]])]
    posts = [niw.post(D)(mu, Sig) for mu, Sig in zip(mus, Sigs)]
    posts2 = [niw(mu, Sig)*niw.likelihood(mu, Sig, D=D) for mu, Sig, in zip(mus, Sigs)]

    np.testing.assert_array_almost_equal(posts/posts[0], posts2/posts2[0], 5,
                                         "NIW posterior not proportional to prior * likelihood.")

    # Check that posterior = prior * likelihood / evidence
    mus = [np.r_[1.1, 1.1], np.r_[1.1, 1.2], np.r_[0.7, 1.3]]
    Sigs = [np.eye(2)*0.2, np.eye(2)*0.1, np.array([[2.1, -0.1], [-0.1, 2.2]])]
    post = niw.post(D)
    post1 = [niw(mu, Sig) * niw.likelihood(mu, Sig, D=D) / niw.evidence(D)
             for mu, Sig in zip(mus, Sigs)]
    post2 = [post(mu, Sig) for mu, Sig in zip(mus, Sigs)]
    np.testing.assert_array_almost_equal(post1, post2, 10,
                                         "NIW posterior != prior * likelihood / evidence")


@timer
def test_GaussianMeanKnownVariance():
    mu_0 = 0.0
    sig_0 = 1.0
    sig = 0.1
    model = prior.GaussianMeanKnownVariance(mu_0, sig_0, sig)

    # Check that we can draw samples from model.
    model.sample()
    model.sample(size=10)

    # Check that we can evaluate a likelihood given 1 data point.
    theta = (1.0, )
    x = 1.0
    model.like1(*theta, x=x)
    # Or given multiple data points.
    D = np.array([1.0, 1.0, 1.0, 1.3])
    model.likelihood(*theta, D=D)

    # Evaluate prior
    model(*theta)
    # Update prior parameters
    model.post_params(D)
    # Prior predictive
    model.pred(x)
    # Posterior predictive
    model.post_pred(D, x)


@timer
def test_NIX_eq_NIG():
    mu_0 = 0.1
    sigsqr_0 = 1.1
    kappa_0 = 2
    nu_0 = 3

    m_0 = mu_0
    V_0 = 1./kappa_0
    a_0 = nu_0/2.0
    b_0 = nu_0*sigsqr_0/2.0

    model1 = prior.NIX(mu_0, kappa_0, sigsqr_0, nu_0)
    model2 = prior.NIG(m_0, V_0, a_0, b_0)

    mus = np.linspace(-2.2, 2.2, 5)
    vars_ = np.linspace(1.0, 4.0, 5)
    xs = np.arange(-1.1, 1.1, 5)

    for x in xs:
        np.testing.assert_equal(
            model1.pred(x), model2.pred(x),
            "NIX and NIG prior predictive densities don't agree at x = ".format(x))
        np.testing.assert_equal(
            model1.post(x).pred(x), model2.post(x).pred(x),
            "NIX and NIG posterior predictive densities don't agree at x = {}".format(x))

    for mu, var in zip(mus, vars_):
        np.testing.assert_almost_equal(
            model1(mu, var), model2(mu, var), 10,
            "NIX and NIG prior densities don't agree at mu, var = {}, {}".format(mu, var))

    post1 = model1.post(xs)
    post2 = model2.post(xs)
    for mu, var in zip(mus, vars_):
        np.testing.assert_almost_equal(
            post1(mu, var), post2(mu, var), 10,
            "NIX and NIG posterior densities don't agree at mu, var = {}, {}".format(mu, var))

    for mu, var, x in zip(mus, vars_, xs):
        np.testing.assert_almost_equal(
            model1.like1(mu, var, x), model2.like1(mu, var, x), 10,
            "NIX and NIG likelihoods don't agree at mu, var, x = {}, {}, {}".format(mu, var, x))

    np.testing.assert_almost_equal(
        model1.evidence(xs), model2.evidence(xs), 10,
        "NIX and NIG evidences don't agree")


@timer
def test_NIX():
    mu_0 = -0.1
    sigsqr_0 = 1.1
    kappa_0 = 2
    nu_0 = 3

    nix = prior.NIX(mu_0, kappa_0, sigsqr_0, nu_0)

    D = [1.0, 2.0, 3.0]
    mus = [1.1, 1.2, 1.3]
    vars_ = [1.2, 3.2, 2.3]

    # Check prior density
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        r = dblquad(nix, 0.0, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5, "NIX prior density does not integrate to 1.0")

    # Check prior predictive density
    r = quad(nix.pred, -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIX prior predictive density does not integrate to 1.0")

    # Check posterior density
    r = dblquad(nix.post(D), 0.0, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 7, "NIX posterior density does not integrate to 1.0")

    # Check posterior predictive density
    r = quad(nix.post(D).pred, -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIX posterior predictive density does not integrate to 1.0")

    # Check that the likelihood integrates to 1.
    r = quad(lambda x: nix.like1(mu=1.1, var=2.1, x=x), -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIX likelihood does not integrate to 1.0")

    # Check that evidence (of single data point) integrates to 1.
    r = quad(lambda x: nix.evidence(x), -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIX evidence does not integrate to 1.0")
    # Check evidence for two data points.
    r = dblquad(lambda x, y: nix.evidence([x, y]),
                -np.inf, np.inf,
                lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5,
                                   "NIX evidence does not integrate to 1.0")

    # Check that posterior = prior * likelihood / evidence
    post = nix.post(D)
    post1 = [nix(mu, var)*nix.likelihood(mu, var, D=D) / nix.evidence(D)
             for mu, var in zip(mus, vars_)]
    post2 = [post(mu, var) for mu, var in zip(mus, vars_)]
    np.testing.assert_array_almost_equal(post1, post2, 10,
                                         "NIX posterior != prior * likelihood / evidence")

    # Test that marginal variance probability method matches integrated result.
    Pr_var1 = [nix.marginal_var(var) for var in vars_]
    Pr_var2 = [quad(lambda mu: nix(mu, var), -np.inf, np.inf)[0] for var in vars_]
    np.testing.assert_array_almost_equal(
        Pr_var1, Pr_var2, 10,
        "Pr(var) method calculation does not match integrated result.")

    # Test that marginal mean probability method matches integrated result.
    Pr_mu1 = [nix.marginal_mu(mu) for mu in mus]
    Pr_mu2 = [quad(lambda var: nix(mu, var), 0.0, np.inf)[0] for mu in mus]
    np.testing.assert_array_almost_equal(
        Pr_mu1, Pr_mu2, 10,
        "Pr(mu) method calculation does not match integrated result.")


@timer
def test_NIG():
    m_0 = -0.1
    V_0 = 1.1
    a_0 = 2.0
    b_0 = 3.0

    nig = prior.NIG(m_0, V_0, a_0, b_0)

    D = [1.0, 2.0, 3.0]
    mus = [1.1, 1.2, 1.3]
    vars_ = [1.2, 3.2, 2.3]

    # Check prior density
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        r = dblquad(nig, 0.0, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5, "NIG prior density does not integrate to 1.0")

    # Check prior predictive density
    r = quad(nig.pred, -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIG prior predictive density does not integrate to 1.0")

    # Check posterior density
    r = dblquad(nig.post(D), 0.0, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 7, "NIG posterior density does not integrate to 1.0")

    # Check posterior predictive density
    r = quad(nig.post(D).pred, -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIG posterior predictive density does not integrate to 1.0")

    # Check that the likelihood integrates to 1.
    r = quad(lambda x: nig.like1(mu=1.1, var=2.1, x=x), -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIG likelihood does not integrate to 1.0")

    # Check that evidence (of single data point) integrates to 1.
    r = quad(lambda x: nig.evidence(x), -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "NIG evidence does not integrate to 1.0")
    # Check evidence for two data points.
    r = dblquad(lambda x, y: nig.evidence([x, y]),
                -np.inf, np.inf,
                lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5,
                                   "NIG evidence does not integrate to 1.0")

    # Check that posterior = prior * likelihood / evidence
    post = nig.post(D)
    post1 = [nig(mu, var)*nig.likelihood(mu, var, D=D) / nig.evidence(D)
             for mu, var in zip(mus, vars_)]
    post2 = [post(mu, var) for mu, var in zip(mus, vars_)]
    np.testing.assert_array_almost_equal(post1, post2, 10,
                                         "NIG posterior != prior * likelihood / evidence")

    # Test that marginal variance probability method matches integrated result.
    Pr_var1 = [nig.marginal_var(var) for var in vars_]
    Pr_var2 = [quad(lambda mu: nig(mu, var), -np.inf, np.inf)[0] for var in vars_]
    np.testing.assert_array_almost_equal(
        Pr_var1, Pr_var2, 10,
        "Pr(var) method calculation does not match integrated result.")

    # Test that marginal mean probability method matches integrated result.
    Pr_mu1 = [nig.marginal_mu(mu) for mu in mus]
    Pr_mu2 = [quad(lambda var: nig(mu, var), 0.0, np.inf)[0] for mu in mus]
    np.testing.assert_array_almost_equal(
        Pr_mu1, Pr_mu2, 10,
        "Pr(mu) method calculation does not match integrated result.")


@timer
def test_InvGamma():
    alpha = 1.1
    beta = 1.2
    mu = 0.1
    ig = prior.InvGamma(alpha, beta, mu)
    ig.sample()

    # Check prior density
    r = quad(ig, 0.0, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5, "InvGamma prior density does not integrate to 1.0")

    # Check prior predictive density
    r = quad(ig.pred, -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "InvGamma prior predictive density does not integrate to 1.0")

    # Check posterior density
    D = [1.0, 2.0, 3.0]
    r = quad(ig.post(D), 0.0, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 7,
                                   "InvGamma posterior density does not integrate to 1.0")

    # Check posterior predictive density
    r = quad(ig.post(D).pred, -np.inf, np.inf)
    np.testing.assert_almost_equal(
        r[0], 1.0, 10, "InvGamma posterior predictive density does not integrate to 1.0")

    # Check that the likelihood integrates to 1.
    r = quad(lambda x: ig.like1(var=2.1, x=x), -np.inf, np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "InvGamma likelihood does not integrate to 1.0")

    # Check that posterior is proportional to prior * likelihood
    # Add some more data points
    D = np.array([1.0, 2.0, 3.0, 2.2, 2.3, 1.2])
    vars_ = [0.7, 1.1, 1.2, 1.5]
    posts = [ig.post(D)(var) for var in vars_]
    posts2 = [ig(var)*ig.likelihood(var, D=D) for var in vars_]

    np.testing.assert_array_almost_equal(
        posts/posts[0], posts2/posts2[0], 5,
        "InvGamma posterior not proportional to prior * likelihood.")

    # Check mean and variance
    mean = 1./beta/(alpha-1.0)
    np.testing.assert_almost_equal(quad(lambda x: ig(x)*x, 0.0, np.inf)[0], mean, 10,
                                   "InvGamma has wrong mean.")
    var = beta**(-2)/(alpha-1)**2/(alpha-2)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        np.testing.assert_almost_equal(quad(lambda x: ig(x)*(x-mean)**2, 0.0, np.inf)[0], var, 5,
                                       "InvGamma has wrong variance.")


@timer
def test_InvWish(full=False):
    nu = 3
    Psi = np.eye(2)+0.1
    mu = np.r_[0.1, 0.2]
    iw = prior.InvWish(nu, Psi, mu)
    iw.sample()
    iw.sample(10)

    # Check prior predictive density
    r = dblquad(lambda x, y: iw.pred([x, y]), -np.inf, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5,
                                   "InvWish prior predictive density does not integrate to 1.0")

    # Check posterior predictive density
    D = np.array([[0.1, 0.2], [0.2, 0.3], [0.1, 0.2], [0.4, 0.3]])
    r = dblquad(lambda x, y: iw.post(D).pred([x, y]), -np.inf, np.inf,
                lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 5,
                                   "InvWish posterior predictive density does not integrate to 1.0")

    # Check that the likelihood of a single point in 2 dimensions integrates to 1.
    r = dblquad(lambda x, y: iw.like1(Sig=np.eye(2)+0.12, x=[x, y]),
                -np.inf, np.inf, lambda x: -np.inf, lambda x: np.inf)
    np.testing.assert_almost_equal(r[0], 1.0, 10,
                                   "InvWish likelihood does not integrate to 1.0")

    if __name__ == "__main__" and full:
        # Check that likelihood of a single point in 3 dimensions integrates to 1.
        iw2 = prior.InvWish(3, np.eye(3), [1]*3)
        r = tplquad(lambda x, y, z: iw2.like1(np.eye(3)+0.1, [x, y, z]),
                    -np.inf, np.inf,
                    lambda x: -np.inf, lambda x: np.inf,
                    lambda x, y: -np.inf, lambda x, y: np.inf)
        np.testing.assert_almost_equal(r[0], 1.0, 8,
                                       "InvWish likelihood does not integrate to 1.0")

    # Check that posterior is proportional to prior * likelihood
    # Add some more data points
    D = np.array([[0.1, 0.2], [0.2, 0.3], [0.1, 0.2], [0.4, 0.3],
                  [2.2, 1.1], [2.3, 1.1], [2.5, 2.3]])
    Sigs = [np.eye(2)*1.5, np.eye(2)*0.7, np.array([[1.1, -0.1], [-0.1, 1.2]])]
    posts = [iw.post(D)(Sig) for Sig in Sigs]
    posts2 = [iw(Sig)*iw.likelihood(Sig, D=D) for Sig in Sigs]

    np.testing.assert_array_almost_equal(
        posts/posts[0], posts2/posts2[0], 5,
        "InvWish posterior not proportional to prior * likelihood.")


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--full', action='store_true', help="Run full test suite (slow).")
    args = parser.parse_args()

    test_NIW(args.full)
    test_GaussianMeanKnownVariance()
    test_NIX_eq_NIG()
    test_NIX()
    test_NIG()
    test_InvGamma()
    test_InvWish(args.full)
