"""Example usage of the lightweight ResearchSkill."""

from tino_storm.skills import ResearchSkill


def main():
    skill = ResearchSkill(cloud_allowed=False)
    topic = "The Eiffel Tower"
    result = skill(topic, vault=None)
    print({"outline": result.outline, "draft": result.draft})

    if skill.cloud_allowed:
        skill.optimize()


if __name__ == "__main__":
    main()
