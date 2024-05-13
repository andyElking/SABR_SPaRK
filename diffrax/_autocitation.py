import functools as ft
import inspect
import re
from collections.abc import Callable
from typing import Optional

import jax
import jax.core
import jax.tree_util as jtu

from ._adjoint import BacksolveAdjoint, DirectAdjoint, RecursiveCheckpointAdjoint
from ._brownian import AbstractBrownianPath, VirtualBrownianTree
from ._heuristics import is_cde, is_sde
from ._integrate import diffeqsolve
from ._misc import adjoint_rms_seminorm
from ._saveat import SubSaveAt
from ._solver import (
    AbstractImplicitSolver,
    AbstractItoSolver,
    AbstractSRK,
    AbstractStratonovichSolver,
    Dopri5,
    Dopri8,
    GeneralShARK,
    Kvaerno3,
    Kvaerno4,
    Kvaerno5,
    LeapfrogMidpoint,
    ReversibleHeun,
    SEA,
    SemiImplicitEuler,
    ShARK,
    SlowRK,
    SPaRK,
    SRA1,
    Tsit5,
)
from ._step_size_controller import PIDController


def citation(*args, **kwargs):
    """Autogenerate a list of BibTeX references for the numerical methods being used.

    **Arguments:**

    `citation` may be called with any subset of the argments to
    [`diffrax.diffeqsolve`][]. To generate the citation list it may be easiest
    to simply replace `diffeqsolve` with `citation`.

    **Returns:**

    Nothing. Prints a BibTeX file to stdout.

    !!! Example

        ```python
        from diffrax import citation, Dopri5, PIDController

        citation(solver=Dopri5(),
                 stepsize_controller=PIDController(pcoeff=0.4, rtol=1e-3, atol=1e-6))

        # % --- AUTOGENERATED REFERENCES PRODUCED USING `diffrax.citation(...)` ---
        # % The following references were found for the numerical techniques being used.
        # % This does not cover e.g. any modelling techniques being used.
        #
        # ...
        # ... Full output truncated in this example!
        # ... Here's what the final entry looks like:
        # ...
        #
        # % The use of a PI-controller to adapt step sizes is from Section IV.2 of:
        # @book{hairer2002solving-ii,
        #   address={Berlin},
        #   author={Hairer, E. and Wanner, G.},
        #   edition={Second Revised Edition},
        #   publisher={Springer},
        #   title={{S}olving {O}rdinary {D}ifferential {E}quations {II} {S}tiff and
        #          {D}ifferential-{A}lgebraic {P}roblems},
        #   year={2002}
        # }
        # % and Sections 1--3 of:
        # @article{soderlind2002automatic,
        #     title={Automatic control and adaptive time-stepping},
        #     author={Gustaf S{\"o}derlind},
        #     year={2002},
        #     journal={Numerical Algorithms},
        #     volume={31},
        #     pages={281--310}
        # }
        #
        # % --- END AUTOGENERATED REFERENCES ---
        ```

    """
    bound = _diffeqsignature.bind_partial(*args, **kwargs)
    kwargs = dict(bound.kwargs)
    for arg_name, arg_value in zip(_diffeqsignature.parameters.keys(), bound.args):
        kwargs[arg_name] = arg_value
    cites = []
    cites.append(_start)
    for rule in citation_rules:
        rule_parameters = list(inspect.signature(rule).parameters.values())
        needed_keys = set()
        has_var = False
        for param in rule_parameters:
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                has_var = True
            else:
                assert param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
                if param.default is inspect.Parameter.empty:
                    needed_keys.add(param.name)
        if not set(kwargs).issuperset(needed_keys):
            continue
        if has_var:
            rulekwargs = kwargs
        else:
            rulekwargs = {
                param.name: kwargs[param.name]
                for param in rule_parameters
                if param.name in kwargs
            }
        cite = rule(**rulekwargs)
        if cite is not None:
            cites.append(cite.strip())
    cites.append(_end)
    print("\n\n".join(cites))


_diffeqsignature = inspect.signature(diffeqsolve)


citation_rules: list[Callable[..., Optional[str]]] = []


_thesis_cite = r"""
phdthesis{kidger2021on,
    title={{O}n {N}eural {D}ifferential {E}quations},
    author={Patrick Kidger},
    year={2021},
    school={University of Oxford},
}
""".strip()

_start = r"""
% --- AUTOGENERATED REFERENCES PRODUCED USING `diffrax.citation(...)` ---
% The following references were found for the numerical techniques being used.
% This does not cover e.g. any modelling techniques being used.
% If you think a paper is missing from here then open an issue or pull request at
% https://github.com/patrick-kidger/diffrax
""".strip()

_end = r"""
% --- END AUTOGENERATED REFERENCES ---
""".strip()


_reference_regex = re.compile(r"```bibtex([^`]*)```")


@ft.lru_cache(maxsize=None)
def _parse_reference(obj) -> str:
    references = _reference_regex.findall(obj.__doc__)
    [reference] = [inspect.cleandoc(ref) for ref in references]
    return reference


@ft.lru_cache(maxsize=None)
def _parse_reference_multi(obj) -> list[str]:
    references = _reference_regex.findall(obj.__doc__)
    return [inspect.cleandoc(ref) for ref in references]


def _no_tracer(x, name):
    if isinstance(x, jax.core.Tracer):
        raise RuntimeError(
            f"`diffrax.citation` was called with {name} as a traced JAX value. Try "
            "running again without this, e.g. using `jax.disable_jit()`."
        )


@citation_rules.append
def _diffrax():
    return (
        r"""
% You are using Diffrax, which is citable as:
"""
        + _thesis_cite
        + r"""

% You are using Equinox, which is citable as:
@article{kidger2021equinox,
    author={Patrick Kidger and Cristian Garcia},
    title={{E}quinox: neural networks in {JAX} via callable {P}y{T}rees and
           filtered transformations},
    year={2021},
    journal={Differentiable Programming workshop at Neural Information Processing
             Systems 2021}
}

% You are using JAX, which is citable as:
@software{jax2018github,
  author = {James Bradbury and Roy Frostig and Peter Hawkins and Matthew James Johnson
            and Chris Leary and Dougal Maclaurin and George Necula and Adam Paszke and
            Jake Vander{P}las and Skye Wanderman-{M}ilne and Qiao Zhang},
  title = {{JAX}: composable transformations of {P}ython+{N}um{P}y programs},
  url = {http://github.com/google/jax},
  version = {"""
        + str(jax.__version__)
        + r"""},
  year = {2018},
}
"""
    )


@citation_rules.append
def _backsolve_adjoint(adjoint, terms=None):
    if type(adjoint) is BacksolveAdjoint:
        if is_sde(terms):
            vbt_ref, _ = _parse_reference_multi(VirtualBrownianTree)
            return (
                r"""
    % You are backpropagating through an SDE using optimise-then-discretise
    % (`adjoint=BacksolveAdjoint(...)`)
    % This technique was introduced in 
    """
                + vbt_ref
                + r"""
    % This technique was refined (simplified via rough path theory) in Section 5.2.3 of:
    """
                + _thesis_cite
            )
        elif is_cde(terms):
            return (
                r"""
    % You are backpropagating through a CDE using optimise-then-discretise
    % (`adjoint=BacksolveAdjoint(...)`)
    % This technique was introduced in Section 5.2.2 of:
    """
                + _thesis_cite
            )
        else:
            return (
                r"""
% You are backpropagating through an ODE using optimise-then-discretise
%  (`adjoint=BacksolveAdjoint(...)`)
% Many references exist for this technique. For example:
@article{chen2018neuralode,
  title={Neural Ordinary Differential Equations},
  author={Chen, Ricky T. Q. and Rubanova, Yulia and Bettencourt, Jesse and Duvenaud,
          David},
  journal={Advances in Neural Information Processing Systems},
  year={2018}
}
% In addition, the most modern (6-line) proof of this result can be found in Section
5.1.2.1 of:
"""
                + _thesis_cite
            )


@citation_rules.append
def _discrete_adjoint(adjoint):
    if type(adjoint) in (RecursiveCheckpointAdjoint, DirectAdjoint):
        pieces = []
        pieces.append(
            r"""
% You are differentiating using discretise-then-optimise.
"""
        )
        pieces.append(
            r"""
% If using forward-mode autodifferentiation, then this was studied in:
@inproceedings{ma2021comparison,
  title={A Comparison of Automatic Differentiation and Continuous Sensitivity Analysis
         for Derivatives of Differential Equation Solutions}, 
  author={Ma, Yingbo and Dixit, Vaibhav and Innes, Michael J and Guo, Xingjian and
          Rackauckas, Chris},
  booktitle={2021 IEEE High Performance Extreme Computing Conference (HPEC)}, 
  year={2021},
  pages={1-9},
  doi={10.1109/HPEC49654.2021.9622796}
}
"""
        )
        if type(adjoint) is RecursiveCheckpointAdjoint:
            pieces.append(
                r"""
% If using reverse-mode autodifferentiation (backpropagation), then you are using
% online recursive checkpointing in order to minimise memory usage. This was developed
% in:
@article{stumm2010new,
    author = {Stumm, Philipp and Walther, Andrea},
    title = {New Algorithms for Optimal Online Checkpointing},
    journal = {SIAM Journal on Scientific Computing},
    volume = {32},
    number = {2},
    pages = {836--854},
    year = {2010},
    doi = {10.1137/080742439},
}
@article{wang2009minimal,
    author = {Wang, Qiqi and Moin, Parviz and Iaccarino, Gianluca},
    title = {Minimal Repetition Dynamic Checkpointing Algorithm for Unsteady
             Adjoint Calculation},
    journal = {SIAM Journal on Scientific Computing},
    volume = {31},
    number = {4},
    pages = {2549--2567},
    year = {2009},
    doi = {10.1137/080727890},
}

% In addition, the equivalent offline recursive checkpointing scheme (also known as
% "treeverse", "binary checkpointing", or "revolve") was developed in:
@article{griewank1992achieving,
    author = {Griewank, Andreas},
    title = {Achieving logarithmic growth of temporal and spatial complexity in
             reverse automatic differentiation},
    journal = {Optimization Methods and Software},
    volume = {1},
    number = {1},
    pages = {35--54},
    year  = {1992},
    publisher = {Taylor & Francis},
    doi = {10.1080/10556789208805505},
}
@article{griewank2000revolve,
    author = {Griewank, Andreas and Walther, Andrea},
    title = {Algorithm 799: Revolve: An Implementation of Checkpointing for the
             Reverse or Adjoint Mode of Computational Differentiation},
    year = {2000},
    publisher = {Association for Computing Machinery},
    volume = {26},
    number = {1},
    doi = {10.1145/347837.347846},
    journal = {ACM Trans. Math. Softw.},
    pages = {19--45},
}
"""
            )
        return "\n".join([p.strip() for p in pieces])


@citation_rules.append
def _virtual_brownian_tree(terms):
    is_vbt = lambda x: isinstance(x, VirtualBrownianTree)
    leaves = jtu.tree_leaves(terms, is_leaf=is_vbt)
    if any(is_vbt(leaf) for leaf in leaves):
        vbt_ref, _ = _parse_reference_multi(VirtualBrownianTree)
        return (
            r"""
% You are simulating Brownian motion using a virtual Brownian tree, which was introduced
% in:
"""
            + vbt_ref
        )


@citation_rules.append
def _space_time_levy_area(terms):
    has_levy_area = lambda x: isinstance(x, AbstractBrownianPath) and x.levy_area != ""
    leaves = jtu.tree_leaves(terms, is_leaf=has_levy_area)
    if any(has_levy_area(leaf) for leaf in leaves):
        _, levy_area_ref = _parse_reference_multi(VirtualBrownianTree)
        return (
            r"""
% You are simulating Brownian motion using space-time Levy area, the formulae for which
% were developed in:
"""
            + levy_area_ref
        )


@citation_rules.append
def _backsolve_rms_norm(adjoint):
    if type(adjoint) is BacksolveAdjoint:
        if adjoint_rms_seminorm in jtu.tree_leaves(adjoint):
            return r"""
% You are backpropagating using adjoint seminorms, which was introduced in::
""" + _parse_reference(adjoint_rms_seminorm)


@citation_rules.append
def _explicit_solver(solver, terms=None):
    if not isinstance(
        solver,
        (
            AbstractImplicitSolver,
            AbstractSRK,
            AbstractItoSolver,
            AbstractStratonovichSolver,
        ),
    ) and not is_sde(terms):
        return r"""
% You are using an explicit solver, and may wish to cite the standard textbook:
@book{hairer2008solving-i,
  address={Berlin},
  author={Hairer, E. and N{\o}rsett, S.P. and Wanner, G.},
  edition={Second Revised Edition},
  publisher={Springer},
  title={{S}olving {O}rdinary {D}ifferential {E}quations {I} {N}onstiff
         {P}roblems},
  year={2008}
}
"""


@citation_rules.append
def _implicit_solver(solver, terms=None):
    if isinstance(solver, AbstractImplicitSolver) and not is_sde(terms):
        return r"""
% You are using an implicit solver, and may wish to cite the standard textbook:
@book{hairer2002solving-ii,
  address={Berlin},
  author={Hairer, E. and Wanner, G.},
  edition={Second Revised Edition},
  publisher={Springer},
  title={{S}olving {O}rdinary {D}ifferential {E}quations {II} {S}tiff and
         {D}ifferential-{A}lgebraic {P}roblems},
  year={2002}
}
"""


@citation_rules.append
def _symplectic_solver(solver, terms=None):
    if type(solver) is SemiImplicitEuler and not is_sde(terms):
        return r"""
You are using a symplectic solver, and may wish to cite the textbook:
@book{hairer2013geometric,
  title={Geometric Numerical Integration: Structure-Preserving Algorithms for Ordinary
         Differential Equations},
  author={Hairer, E. and Lubich, C. and Wanner, G.},
  isbn={9783662050187},
  series={Springer Series in Computational Mathematics},
  year={2013},
  publisher={Springer Berlin Heidelberg}
}

"""


@citation_rules.append
def _cde(terms):
    if is_cde(terms):
        return r"""
% You are solving a CDE. These were studied in:
@incollection{kidger2020neuralcde,
    title={Neural Controlled Differential Equations for Irregular Time Series},
    author={Kidger, Patrick and Morrill, James and Foster, James and Lyons, Terry},
    booktitle={Advances in Neural Information Processing Systems},
    publisher={Curran Associates, Inc.},
    year={2020},
}
"""


@citation_rules.append
def _sde(terms):
    if is_sde(terms):
        return r"""
% You are solving an SDE, and may wish to cite the textbook:
@book{kloeden2011numerical,
  title={Numerical Solution of Stochastic Differential Equations},
  author={Kloeden, P.E. and Platen, E.},
  isbn={9783540540625},
  series={Stochastic Modelling and Applied Probability},
  year={2011},
  publisher={Springer Berlin Heidelberg}
}
"""


_is_subsaveat = lambda x: isinstance(x, SubSaveAt)


@citation_rules.append
def _solvers(solver, saveat=None):
    if type(solver) in (
        Tsit5,
        Kvaerno3,
        Kvaerno4,
        Kvaerno5,
        ReversibleHeun,
        LeapfrogMidpoint,
        ShARK,
        SRA1,
        SlowRK,
        GeneralShARK,
        SPaRK,
        SEA,
    ):
        return (
            r"""
% You are using the """
            + solver.__class__.__name__
            + r""" solver, which was introduced in:
"""
            + _parse_reference(solver)
        )
    elif type(solver) is Dopri5:
        ref1, ref2 = _parse_reference_multi(Dopri5)
        assert "Dormand" in ref1
        assert "Prince" in ref1
        assert "Shampine" in ref2
        return (
            r"""
% Dormand--Prince 5(4) was introduced in:
"""
            + ref1
            + r"""
% The specific implementation used here is the improved version (different Butcher
% tableau) introduced in:
"""
            + ref2
        )
    elif type(solver) is Dopri8:
        ref1, ref2 = _parse_reference_multi(Dopri8)
        assert "Dormand" in ref1
        assert "Prince" in ref1
        assert "Bogacki" in ref2
        assert "Shampine" in ref2
        msg = (
            r"""
% Dormand--Prince 8(7) was introduced in:
"""
            + ref1
        )
        if saveat is not None and (
            saveat.dense
            or (
                subsaveat.ts is not None
                for subsaveat in jtu.tree_leaves(saveat, is_leaf=_is_subsaveat)
            )
        ):
            msg += (
                r"""
% Output via `SaveAt(ts=...)` or `SaveAt(dense=True)` is done using the
% Dormand--Prince 8(7) interpolant introduced in:
"""
                + ref2
            )
        return msg


@citation_rules.append
def _auto_dt0(dt0):
    if dt0 is None:
        return r"""
% Automatic selection of initial step size is from Section II.4 of:
@book{hairer2008solving-i,
  address={Berlin},
  author={Hairer, E. and N{\o}rsett, S.P. and Wanner, G.},
  edition={Second Revised Edition},
  publisher={Springer},
  title={{S}olving {O}rdinary {D}ifferential {E}quations {I} {N}onstiff
         {P}roblems},
  year={2008}
}
"""


@citation_rules.append
def _pid_controller(stepsize_controller, terms=None):
    if type(stepsize_controller) is PIDController:
        if is_sde(terms):
            return r"""
% The use of PI and PI controllers to adapt step sizes for SDEs are from:
@article{burrage2004adaptive,
  title={Adaptive stepsize based on control theory for stochastic
         differential equations},
  journal={Journal of Computational and Applied Mathematics},
  volume={170},
  number={2},
  pages={317--336},
  year={2004},
  doi={https://doi.org/10.1016/j.cam.2004.01.027},
  author={P.M. Burrage and R. Herdiana and K. Burrage},
}
@article{ilie2015adaptive,
  author={Ilie, Silvana and Jackson, Kenneth R. and Enright, Wayne H.},
  title={{A}daptive {T}ime-{S}tepping for the {S}trong {N}umerical {S}olution
         of {S}tochastic {D}ifferential {E}quations},
  year={2015},
  publisher={Springer-Verlag},
  address={Berlin, Heidelberg},
  volume={68},
  number={4},
  doi={https://doi.org/10.1007/s11075-014-9872-6},
  journal={Numer. Algorithms},
  pages={791–-812},
}
"""
        else:
            no_p = stepsize_controller.pcoeff == 0
            no_d = stepsize_controller.dcoeff == 0
            _no_tracer(no_p, "stepsize_controller.pcoeff")
            _no_tracer(no_d, "stepsize_controller.dcoeff")
            if no_d:
                if no_p:
                    return r"""
% The use of an I-controller to adapt step sizes is from Section II.4 of:
@book{hairer2008solving-i,
  address={Berlin},
  author={Hairer, E. and N{\o}rsett, S.P. and Wanner, G.},
  edition={Second Revised Edition},
  publisher={Springer},
  title={{S}olving {O}rdinary {D}ifferential {E}quations {I} {N}onstiff
         {P}roblems},
  year={2008}
}
"""
                else:
                    return r"""
% The use of a PI-controller to adapt step sizes is from Section IV.2 of:
@book{hairer2002solving-ii,
  address={Berlin},
  author={Hairer, E. and Wanner, G.},
  edition={Second Revised Edition},
  publisher={Springer},
  title={{S}olving {O}rdinary {D}ifferential {E}quations {II} {S}tiff and
         {D}ifferential-{A}lgebraic {P}roblems},
  year={2002}
}
% and Sections 1--3 of:
@article{soderlind2002automatic,
    title={Automatic control and adaptive time-stepping},
    author={Gustaf S{\"o}derlind},
    year={2002},
    journal={Numerical Algorithms},
    volume={31},
    pages={281--310}
}
"""
            else:
                return r"""
% The use of a PID controller to adapt step sizes is from:
@article{soderlind2003digital,
    title={{D}igital {F}ilters in {A}daptive {T}ime-{S}tepping,
    author={Gustaf S{\"o}derlind},
    year={2003},
    journal={ACM Transactions on Mathematical Software},
    volume={20},
    number={1},
    pages={1--26}
}
"""
