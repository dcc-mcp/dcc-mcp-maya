"""Unit tests for the maya-particles skill and its contract module."""

from __future__ import annotations

import pytest
from conftest import load_and_call

from dcc_mcp_maya.particles import (
    CYCLE_MODES,
    EMITTER_TYPES,
    NPARTICLE_ATTRS,
    PARTICLE_ATTRS,
    ParticleContractError,
    create_emitter,
    create_particle_instancer,
    create_particle_system,
    list_particles,
    set_emitter_properties,
    set_particle_properties,
)


class _FakeCmds:
    """Minimal ``maya.cmds`` stand-in that records calls for assertions."""

    def __init__(self, node_type="nParticle", existing=None, created=None):
        self.node_type = node_type
        self.existing = existing or {}
        self.created = created or {}
        self.calls = []
        self.counters = {}

    def objExists(self, node):
        return node in self.existing or node in self.created

    def nodeType(self, node):
        return self.existing.get(node) or self.created.get(node) or self.node_type

    def ls(self, **kwargs):
        node_type = kwargs.get("type")
        if node_type is None:
            return []
        return [name for name, kind in self.created.items() if kind == node_type]

    def listRelatives(self, node, **_kwargs):
        return ["|{}Parent".format(node)]

    def listConnections(self, node, **_kwargs):
        return []

    def _next(self, prefix):
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return "{}{}".format(prefix, self.counters[prefix])

    def nParticle(self, **kwargs):
        self.calls.append(("nParticle", kwargs))
        name = kwargs.get("name") or self._next("nParticleShape")
        self.created[name] = "nParticle"
        return [name]

    def particle(self, **kwargs):
        self.calls.append(("particle", kwargs))
        name = kwargs.get("name") or self._next("particleShape")
        self.created[name] = "particle"
        return [name]

    def emitter(self, **kwargs):
        self.calls.append(("emitter", kwargs))
        name = kwargs.get("name") or self._next("emitter")
        self.created[name] = "pointEmitter"
        return [name]

    def particleInstancer(self, node, **kwargs):
        self.calls.append(("particleInstancer", node, kwargs))
        name = kwargs.get("name") or self._next("instancer")
        self.created[name] = "instancer"
        return [name]

    def connectDynamic(self, node, **kwargs):
        self.calls.append(("connectDynamic", node, kwargs))

    def setAttr(self, plug, *args, **kwargs):
        self.calls.append(("setAttr", plug, args, kwargs))

    def getAttr(self, plug):
        return 42


def _setattr_calls(cmds):
    return {call[1]: call[2] for call in cmds.calls if call[0] == "setAttr"}


# ---------------------------------------------------------------------------
# create_particle_system
# ---------------------------------------------------------------------------


def test_create_nparticle_system_sets_requested_properties():
    cmds = _FakeCmds()

    result = create_particle_system(
        cmds,
        kind="nparticle",
        name="dust",
        position=[0.0, 1.0, 0.0],
        properties={"lifespan": 2.5, "radius": 0.1},
    )

    assert result["kind"] == "nparticle"
    assert result["shape"] == "dust"
    assert result["properties"] == {"lifespan": 2.5, "radius": 0.1}
    factory_call = [call for call in cmds.calls if call[0] == "nParticle"][0][1]
    assert factory_call["name"] == "dust"
    assert factory_call["position"] == [0.0, 1.0, 0.0]
    applied = _setattr_calls(cmds)
    assert applied["dust.lifespan"] == (2.5,)
    assert applied["dust.radius"] == (0.1,)


def test_create_classic_particle_system_uses_particle_factory():
    cmds = _FakeCmds()

    result = create_particle_system(cmds, kind="classic", properties={"conserve": 0.9})

    assert result["kind"] == "classic"
    assert [call[0] for call in cmds.calls].count("particle") == 1
    assert _setattr_calls(cmds)["particleShape1.conserve"] == (0.9,)


def test_create_particle_system_rejects_unknown_kind():
    with pytest.raises(ParticleContractError, match="kind must be"):
        create_particle_system(_FakeCmds(), kind="fluid")


def test_create_particle_system_rejects_bad_position_arity():
    with pytest.raises(ParticleContractError, match="position expects 3"):
        create_particle_system(_FakeCmds(), position=[0.0, 1.0])


def test_create_particle_system_rejects_unknown_property():
    with pytest.raises(ParticleContractError, match="Unsupported attribute"):
        create_particle_system(_FakeCmds(), properties={"not_an_attr": 1.0})


def test_emitter_types_cover_the_maya_family():
    assert set(EMITTER_TYPES) == {"omni", "directional", "surface", "curve", "volume"}


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def test_create_emitter_connects_targets():
    cmds = _FakeCmds(existing={"nParticleShape1": "nParticle"})

    result = create_emitter(
        cmds,
        emitter_type="volume",
        name="dustEmitter",
        targets=["nParticleShape1"],
        properties={"rate": 250.0},
    )

    assert result["emitter"] == "dustEmitter"
    assert result["emitter_type"] == "volume"
    assert result["targets"] == ["nParticleShape1"]
    factory_call = [call for call in cmds.calls if call[0] == "emitter"][0][1]
    assert factory_call["type"] == "volume"
    connect = [call for call in cmds.calls if call[0] == "connectDynamic"][0]
    assert connect[2] == {"em": "dustEmitter"}


def test_create_emitter_rejects_unknown_type():
    with pytest.raises(ParticleContractError, match="emitter_type must be one of"):
        create_emitter(_FakeCmds(), emitter_type="sprinkler")


def test_create_emitter_rejects_missing_target():
    with pytest.raises(ParticleContractError, match="Particle node does not exist"):
        create_emitter(_FakeCmds(), targets=["ghost"])


def test_set_emitter_properties_edits_only_supplied_values():
    cmds = _FakeCmds(existing={"emitter1": "pointEmitter"})

    result = set_emitter_properties(cmds, emitters=["emitter1"], properties={"rate": 100.0, "speed": 3.0})

    assert result["count"] == 1
    applied = _setattr_calls(cmds)
    assert applied["emitter1.rate"] == (100.0,)
    assert applied["emitter1.speed"] == (3.0,)
    assert "emitter1.spread" not in applied


def test_set_emitter_properties_rejects_empty_payload():
    with pytest.raises(ParticleContractError, match="at least one attribute"):
        set_emitter_properties(_FakeCmds(), emitters=["emitter1"], properties={})


# ---------------------------------------------------------------------------
# set_particle_properties
# ---------------------------------------------------------------------------


def test_set_particle_properties_targets_nparticle_shape_directly():
    cmds = _FakeCmds(existing={"nParticleShape1": "nParticle"})

    result = set_particle_properties(cmds, nodes=["nParticleShape1"], properties={"drag": 0.2, "mass": 2.0})

    assert result["count"] == 1
    applied = _setattr_calls(cmds)
    assert applied["nParticleShape1.drag"] == (0.2,)
    assert applied["nParticleShape1.mass"] == (2.0,)


def test_set_particle_properties_resolves_transform_to_shape():
    cmds = _FakeCmds(existing={"group1": "transform"})
    cmds.listRelatives = lambda node, **_kwargs: ["nParticleShape1"]
    cmds.created = {"nParticleShape1": "nParticle"}

    result = set_particle_properties(cmds, nodes=["group1"], properties={"conserve": 0.5})

    assert result["updated"][0]["particle"] == "nParticleShape1"
    assert _setattr_calls(cmds)["nParticleShape1.conserve"] == (0.5,)


def test_set_particle_properties_rejects_missing_node():
    with pytest.raises(ParticleContractError, match="Node does not exist"):
        set_particle_properties(_FakeCmds(), nodes=["ghost"], properties={"mass": 1.0})


def test_nparticle_attrs_mapping_exposes_snake_case_keys():
    assert "lifespan_mode" in NPARTICLE_ATTRS
    assert NPARTICLE_ATTRS["particle_render_type"] == "particleRenderType"
    assert NPARTICLE_ATTRS["self_collide_width_scale"] == "selfCollideWidthScale"


def test_particle_attrs_do_not_expose_reserved_or_invalid_plugs():
    """`for` is a Python keyword and not a particle plug; setAttr would fail."""
    assert "for" not in PARTICLE_ATTRS
    assert "for" not in NPARTICLE_ATTRS


# ---------------------------------------------------------------------------
# Instancing
# ---------------------------------------------------------------------------


def test_create_particle_instancer_uses_add_object():
    cmds = _FakeCmds(existing={"nParticleShape1": "nParticle", "pRock1": "transform"})

    result = create_particle_instancer(
        cmds,
        particle="nParticleShape1",
        objects=["pRock1"],
        cycle="sequential",
    )

    assert result["particle"] == "nParticleShape1"
    assert result["objects"] == ["pRock1"]
    assert result["cycle"] == "sequential"
    _op, node, kwargs = [call for call in cmds.calls if call[0] == "particleInstancer"][0]
    assert node == "nParticleShape1"
    assert kwargs["addObject"] is True
    assert kwargs["object"] == ["pRock1"]


def test_create_particle_instancer_rejects_bad_cycle():
    cmds = _FakeCmds(existing={"nParticleShape1": "nParticle", "pRock1": "transform"})
    with pytest.raises(ParticleContractError, match="cycle must be one of"):
        create_particle_instancer(cmds, particle="nParticleShape1", objects=["pRock1"], cycle="sometimes")


def test_create_particle_instancer_rejects_random_cycle_unsupported_by_maya():
    """Maya's -cycle only accepts none/sequential; random is rejected by the command."""
    cmds = _FakeCmds(existing={"nParticleShape1": "nParticle", "pRock1": "transform"})
    with pytest.raises(ParticleContractError, match="cycle must be one of"):
        create_particle_instancer(cmds, particle="nParticleShape1", objects=["pRock1"], cycle="random")
    assert "random" not in CYCLE_MODES


def test_create_particle_instancer_requires_sources():
    cmds = _FakeCmds(existing={"nParticleShape1": "nParticle"})
    with pytest.raises(ParticleContractError, match="at least one source object"):
        create_particle_instancer(cmds, particle="nParticleShape1", objects=[])


# ---------------------------------------------------------------------------
# list_particles
# ---------------------------------------------------------------------------


def test_list_particles_summarises_systems_emitters_and_instancers():
    cmds = _FakeCmds()
    cmds.created = {
        "nParticleShape1": "nParticle",
        "particleShape1": "particle",
        "emitter1": "pointEmitter",
        "instancer1": "instancer",
    }

    result = list_particles(cmds)

    assert result["counts"] == {"particle_systems": 2, "emitters": 1, "instancers": 1}
    kinds = {record["kind"] for record in result["particle_systems"]}
    assert kinds == {"nparticle", "classic"}
    assert result["emitters"][0]["emitter"] == "emitter1"
    assert result["instancers"][0]["instancer"] == "instancer1"


def test_list_particles_can_hide_emitters_and_instancers():
    cmds = _FakeCmds()
    cmds.created = {"nParticleShape1": "nParticle", "emitter1": "pointEmitter", "instancer1": "instancer"}

    result = list_particles(cmds, include_emitters=False, include_instancers=False)

    assert result["counts"] == {"particle_systems": 1, "emitters": 0, "instancers": 0}


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def test_skill_create_particle_system_returns_success_envelope():
    cmds = _FakeCmds()

    result = load_and_call(
        "maya-particles/scripts/create_particle_system.py",
        cmds,
        "main",
        kind="nparticle",
        name="dust",
        lifespan=2.0,
    )

    assert result["success"] is True, result
    assert result["context"]["shape"] == "dust"
    assert result["context"]["kind"] == "nparticle"
    assert result["context"]["properties"] == {"lifespan": 2.0}


def test_skill_create_particle_system_rejects_unknown_kind():
    result = load_and_call(
        "maya-particles/scripts/create_particle_system.py",
        _FakeCmds(),
        "main",
        kind="fluid",
    )

    assert result["success"] is False
    assert "kind" in result["error"]


def test_skill_list_particles_reports_counts():
    cmds = _FakeCmds()
    cmds.created = {"nParticleShape1": "nParticle"}

    result = load_and_call("maya-particles/scripts/list_particles.py", cmds, "main")

    assert result["success"] is True, result
    assert result["context"]["counts"]["particle_systems"] == 1


def test_skill_create_emitter_requires_existing_target():
    result = load_and_call(
        "maya-particles/scripts/create_emitter.py",
        _FakeCmds(),
        "main",
        targets=["ghost"],
    )

    assert result["success"] is False


def test_skill_set_particle_properties_rejects_empty_payload():
    result = load_and_call(
        "maya-particles/scripts/set_particle_properties.py",
        _FakeCmds(existing={"nParticleShape1": "nParticle"}),
        "main",
        nodes=["nParticleShape1"],
    )

    assert result["success"] is False
