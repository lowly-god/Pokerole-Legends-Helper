import json
import random
import discord
from discord import app_commands
from discord.ext import commands


def roll_d6(pool):
    rolls = [random.randint(1, 6) for _ in range(pool)]
    successes = sum(1 for r in rolls if r >= 4)
    return rolls, successes


def format_rolls(rolls):
    return ", ".join(f"**{r}**" if r >= 4 else str(r) for r in rolls)


class TrainerPoolModal(discord.ui.Modal):
    def __init__(self, dc, pokemon_pool, pokemon_rolls, pokemon_successes, pokemon_will_spent=0):
        super().__init__(title="Trainer's Dice Pool")
        self.dc = dc
        self.pokemon_pool = pokemon_pool
        self.pokemon_rolls = pokemon_rolls
        self.pokemon_successes = pokemon_successes
        self.pokemon_will_spent = pokemon_will_spent

        self.trainer_pool = discord.ui.TextInput(
            label="Trainer's Dice Pool",
            placeholder="Enter number of d6s",
            required=True,
            max_length=3
        )
        self.add_item(self.trainer_pool)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            base_pool = int(self.trainer_pool.value)
        except ValueError:
            await interaction.response.send_message(
                "Trainer's Dice Pool must be a whole number.",
                ephemeral=True
            )
            return

        if base_pool < 0 or base_pool > 100:
            await interaction.response.send_message(
                "Trainer's Dice Pool must be between 0 and 100.",
                ephemeral=True
            )
            return

        total_pool = base_pool + self.dc
        rolls, successes = roll_d6(total_pool)

        embed = discord.Embed(title="Training Session — Trainer Roll")
        embed.add_field(name="Set DC", value=str(self.dc), inline=False)
        embed.add_field(
            name="Pokémon's Dice Pool",
            value=(
                f"{self.pokemon_pool}d6\n"
                f"{format_rolls(self.pokemon_rolls)}\n"
                f"**{self.pokemon_successes} successes**"
            ),
            inline=False
        )
        if self.pokemon_will_spent:
            embed.add_field(
                name="Pokémon Roll Will Spent",
                value=f"**{self.pokemon_will_spent}**",
                inline=False
            )
        embed.add_field(
            name="Trainer's Dice Pool",
            value=(
                f"{base_pool}d6 + {self.dc}d6 from Set DC = **{total_pool}d6**\n"
                f"{format_rolls(rolls)}\n"
                f"**{successes} successes**"
            ),
            inline=False
        )
        embed.add_field(
            name="Next Step",
            value=(
                "You may spend Will Points to reroll failed Trainer dice before "
                "finalizing the Training Points, or accept this result."
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            view=TrainerResultView(
                self.dc,
                self.pokemon_pool,
                self.pokemon_rolls,
                self.pokemon_successes,
                base_pool,
                rolls,
                self.pokemon_will_spent,
                0
            )
        )


class TrainerWillRerollModal(discord.ui.Modal):
    def __init__(
        self,
        dc,
        pokemon_pool,
        pokemon_rolls,
        pokemon_successes,
        trainer_base_pool,
        trainer_rolls,
        pokemon_will_spent=0,
        trainer_will_spent=0
    ):
        super().__init__(title="Spend Will on Trainer Roll")
        self.dc = dc
        self.pokemon_pool = pokemon_pool
        self.pokemon_rolls = pokemon_rolls
        self.pokemon_successes = pokemon_successes
        self.trainer_base_pool = trainer_base_pool
        self.trainer_rolls = trainer_rolls
        self.pokemon_will_spent = pokemon_will_spent
        self.trainer_will_spent = trainer_will_spent

        failed_dice = sum(1 for r in trainer_rolls if r < 4)
        self.amount = discord.ui.TextInput(
            label="Will Points to Spend",
            placeholder=f"Enter 1-{failed_dice}",
            required=True,
            max_length=3
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        failed_indices = [i for i, r in enumerate(self.trainer_rolls) if r < 4]
        failed_dice = len(failed_indices)

        try:
            amount = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message(
                "Will Points must be a whole number.",
                ephemeral=True
            )
            return

        if amount < 1 or amount > failed_dice:
            await interaction.response.send_message(
                f"You may spend between 1 and {failed_dice} Will Points.",
                ephemeral=True
            )
            return

        new_rolls = list(self.trainer_rolls)
        rerolled = []

        for index in failed_indices[:amount]:
            new_result = random.randint(1, 6)
            new_rolls[index] = new_result
            rerolled.append(new_result)

        successes = sum(1 for r in new_rolls if r >= 4)
        total_trainer_will = self.trainer_will_spent + amount

        embed = discord.Embed(title="Training Session — Trainer Will Reroll")
        embed.add_field(name="Set DC", value=str(self.dc), inline=False)
        embed.add_field(
            name="Will Spent This Time",
            value=f"**{amount}**",
            inline=False
        )
        embed.add_field(
            name="Rerolled Failed Trainer Dice",
            value=format_rolls(rerolled),
            inline=False
        )
        embed.add_field(
            name="Updated Trainer Roll",
            value=(
                f"{format_rolls(new_rolls)}\n"
                f"**{successes} successes**"
            ),
            inline=False
        )
        embed.add_field(
            name="Trainer Roll Will Spent",
            value=f"**{total_trainer_will}**",
            inline=False
        )
        embed.add_field(
            name="Next Step",
            value=(
                "You may spend more Will Points to reroll remaining failed Trainer dice, "
                "or finalize this result."
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            view=TrainerResultView(
                self.dc,
                self.pokemon_pool,
                self.pokemon_rolls,
                self.pokemon_successes,
                self.trainer_base_pool,
                new_rolls,
                self.pokemon_will_spent,
                total_trainer_will
            )
        )


class TrainerResultView(discord.ui.View):
    def __init__(
        self,
        dc,
        pokemon_pool,
        pokemon_rolls,
        pokemon_successes,
        trainer_base_pool,
        trainer_rolls,
        pokemon_will_spent=0,
        trainer_will_spent=0
    ):
        super().__init__(timeout=120)
        self.dc = dc
        self.pokemon_pool = pokemon_pool
        self.pokemon_rolls = pokemon_rolls
        self.pokemon_successes = pokemon_successes
        self.trainer_base_pool = trainer_base_pool
        self.trainer_rolls = trainer_rolls
        self.pokemon_will_spent = pokemon_will_spent
        self.trainer_will_spent = trainer_will_spent

    @discord.ui.button(
        label="Spend Will Points",
        style=discord.ButtonStyle.success
    )
    async def spend_will(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        failed_dice = sum(1 for r in self.trainer_rolls if r < 4)
        if failed_dice <= 0:
            await interaction.response.send_message(
                "There are no failed Trainer dice left to reroll.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TrainerWillRerollModal(
                self.dc,
                self.pokemon_pool,
                self.pokemon_rolls,
                self.pokemon_successes,
                self.trainer_base_pool,
                self.trainer_rolls,
                self.pokemon_will_spent,
                self.trainer_will_spent
            )
        )

    @discord.ui.button(
        label="Finalize Training",
        style=discord.ButtonStyle.primary
    )
    async def finalize_training(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        successes = sum(1 for r in self.trainer_rolls if r >= 4)
        total_pool = self.trainer_base_pool + self.dc

        embed = discord.Embed(title="Training Session — Complete")
        embed.add_field(name="Set DC", value=str(self.dc), inline=False)
        embed.add_field(
            name="Pokémon's Dice Pool",
            value=(
                f"{self.pokemon_pool}d6\n"
                f"{format_rolls(self.pokemon_rolls)}\n"
                f"**{self.pokemon_successes} successes**"
            ),
            inline=False
        )
        embed.add_field(
            name="Trainer's Dice Pool",
            value=(
                f"{self.trainer_base_pool}d6 + {self.dc}d6 from Set DC = **{total_pool}d6**\n"
                f"{format_rolls(self.trainer_rolls)}\n"
                f"**{successes} successes**"
            ),
            inline=False
        )
        if self.pokemon_will_spent:
            embed.add_field(
                name="Pokémon Roll Will Spent",
                value=f"**{self.pokemon_will_spent}**",
                inline=False
            )
        if self.trainer_will_spent:
            embed.add_field(
                name="Trainer Roll Will Spent",
                value=f"**{self.trainer_will_spent}**",
                inline=False
            )
        embed.add_field(
            name="Result",
            value=(
                f"Your Pokémon gains **{successes} Training Points**.\n"
                "You and your Pokémon gain back **2 Will Points**."
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)


class ContinueTrainingView(discord.ui.View):
    def __init__(self, dc, pokemon_pool, pokemon_rolls, pokemon_successes, will_spent=0):
        super().__init__(timeout=120)
        self.dc = dc
        self.pokemon_pool = pokemon_pool
        self.pokemon_rolls = pokemon_rolls
        self.pokemon_successes = pokemon_successes
        self.will_spent = will_spent

    @discord.ui.button(
        label="Enter Trainer's Dice Pool",
        style=discord.ButtonStyle.primary
    )
    async def enter_trainer_pool(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            TrainerPoolModal(
                self.dc,
                self.pokemon_pool,
                self.pokemon_rolls,
                self.pokemon_successes,
                self.will_spent
            )
        )


class WillRerollModal(discord.ui.Modal):
    def __init__(self, dc, pokemon_pool, pokemon_rolls, will_spent=0):
        super().__init__(title="Spend Will Points")
        self.dc = dc
        self.pokemon_pool = pokemon_pool
        self.pokemon_rolls = pokemon_rolls
        self.will_spent = will_spent

        failed_dice = sum(1 for r in pokemon_rolls if r < 4)
        self.amount = discord.ui.TextInput(
            label="Will Points to Spend",
            placeholder=f"Enter 1-{failed_dice}",
            required=True,
            max_length=3
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        failed_indices = [i for i, r in enumerate(self.pokemon_rolls) if r < 4]
        failed_dice = len(failed_indices)

        try:
            amount = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message(
                "Will Points must be a whole number.",
                ephemeral=True
            )
            return

        if amount < 1 or amount > failed_dice:
            await interaction.response.send_message(
                f"You may spend between 1 and {failed_dice} Will Points.",
                ephemeral=True
            )
            return

        new_rolls = list(self.pokemon_rolls)
        rerolled = []

        for index in failed_indices[:amount]:
            new_result = random.randint(1, 6)
            new_rolls[index] = new_result
            rerolled.append(new_result)

        successes = sum(1 for r in new_rolls if r >= 4)
        total_will = self.will_spent + amount

        embed = discord.Embed(title="Training Session — Pokémon Will Reroll")
        embed.add_field(name="Set DC", value=str(self.dc), inline=False)
        embed.add_field(name="Will Spent This Time", value=f"**{amount}**", inline=False)
        embed.add_field(name="Rerolled Failed Dice", value=format_rolls(rerolled), inline=False)
        embed.add_field(
            name="Updated Pokémon Roll",
            value=f"{format_rolls(new_rolls)}\n**{successes} successes**",
            inline=False
        )
        embed.add_field(name="Total Pokémon Roll Will Spent", value=f"**{total_will}**", inline=False)

        if successes >= self.dc:
            embed.add_field(
                name="Result",
                value=(
                    f"The Pokémon now meets **DC {self.dc}**.\n"
                    "Continue to the Trainer's Dice Pool."
                ),
                inline=False
            )
            await interaction.response.send_message(
                embed=embed,
                view=ContinueTrainingView(
                    self.dc, self.pokemon_pool, new_rolls, successes, total_will
                )
            )
        else:
            embed.add_field(
                name="Result",
                value=(
                    f"The Pokémon still has not met **DC {self.dc}**.\n"
                    "You may spend more Will Points to reroll additional failed dice, "
                    "or accept the failure."
                ),
                inline=False
            )
            await interaction.response.send_message(
                embed=embed,
                view=FailedTrainingView(
                    self.dc, self.pokemon_pool, new_rolls, total_will
                )
            )


class FailedTrainingView(discord.ui.View):
    def __init__(self, dc, pokemon_pool, pokemon_rolls, will_spent=0):
        super().__init__(timeout=120)
        self.dc = dc
        self.pokemon_pool = pokemon_pool
        self.pokemon_rolls = pokemon_rolls
        self.will_spent = will_spent

    @discord.ui.button(
        label="Spend Will Points",
        style=discord.ButtonStyle.success
    )
    async def spend_will(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        failed_dice = sum(1 for r in self.pokemon_rolls if r < 4)
        if failed_dice <= 0:
            await interaction.response.send_message(
                "There are no failed dice left to reroll.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            WillRerollModal(
                self.dc,
                self.pokemon_pool,
                self.pokemon_rolls,
                self.will_spent
            )
        )

    @discord.ui.button(
        label="Accept Failure",
        style=discord.ButtonStyle.danger
    )
    async def accept_failure(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        successes = sum(1 for r in self.pokemon_rolls if r >= 4)

        embed = discord.Embed(title="Training Session — Failed")
        embed.add_field(name="Set DC", value=str(self.dc), inline=False)
        embed.add_field(
            name="Pokémon's Dice Pool",
            value=(
                f"{self.pokemon_pool}d6\n"
                f"{format_rolls(self.pokemon_rolls)}\n"
                f"**{successes} successes**"
            ),
            inline=False
        )
        if self.will_spent:
            embed.add_field(
                name="Pokémon Roll Will Spent",
                value=f"**{self.will_spent}**",
                inline=False
            )
        embed.add_field(
            name="Result",
            value=f"The Pokémon failed to meet **DC {self.dc}**.",
            inline=False
        )
        await interaction.response.send_message(embed=embed)


class PokemonPoolModal(discord.ui.Modal):
    def __init__(self, dc):
        super().__init__(title="Pokémon's Dice Pool")
        self.dc = dc
        self.pokemon_pool = discord.ui.TextInput(
            label="Pokémon's Dice Pool",
            placeholder="Enter number of d6s",
            required=True,
            max_length=3
        )
        self.add_item(self.pokemon_pool)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pool = int(self.pokemon_pool.value)
        except ValueError:
            await interaction.response.send_message(
                "Pokémon's Dice Pool must be a whole number.",
                ephemeral=True
            )
            return

        if pool < 1 or pool > 100:
            await interaction.response.send_message(
                "Pokémon's Dice Pool must be between 1 and 100.",
                ephemeral=True
            )
            return

        rolls, successes = roll_d6(pool)

        embed = discord.Embed(title="Training Session")
        embed.add_field(name="Set DC", value=str(self.dc), inline=False)
        embed.add_field(
            name="Pokémon's Dice Pool",
            value=(
                f"{pool}d6\n"
                f"{format_rolls(rolls)}\n"
                f"**{successes} successes**"
            ),
            inline=False
        )

        if successes < self.dc:
            embed.add_field(
                name="Result",
                value=(
                    f"The Pokémon failed to meet **DC {self.dc}**.\n"
                    "You may spend Will Points to reroll failed dice, or accept the failure."
                ),
                inline=False
            )
            await interaction.response.send_message(
                embed=embed,
                view=FailedTrainingView(self.dc, pool, rolls)
            )
            return

        embed.title = "Training Session — Pokémon Passed"
        embed.add_field(
            name="Next Step",
            value="The Pokémon met the DC. Click below to enter the Trainer's Dice Pool.",
            inline=False
        )
        await interaction.response.send_message(
            embed=embed,
            view=ContinueTrainingView(self.dc, pool, rolls, successes)
        )


class DCSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"DC {n}", value=str(n))
            for n in range(1, 6)
        ]
        super().__init__(
            placeholder="Set DC",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        dc = int(self.values[0])
        await interaction.response.send_modal(PokemonPoolModal(dc))


class DCView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(DCSelect())


class TrainingReferenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("training_reference_data.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)

    @app_commands.command(
        name="training_session",
        description="Roll a Pokémon training session"
    )
    async def trainingsession(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Training Session**\nChoose the Training DC:",
            view=DCView()
        )

    @app_commands.command(
        name="battle_training_points",
        description="Display Battle Training Point rewards"
    )
    async def battletrainingpoints(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "## Battle Training Points\n" + self.data["battletrainingpoints"]
        )

    @app_commands.command(
        name="evolution_time",
        description="Display Training Points required for each evolution speed"
    )
    async def evolutiontime(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "## Evolution Time\n" + self.data["evolutiontime"]
        )

    @app_commands.command(
        name="learning_new_moves",
        description="Display Training Point costs for learning Moves"
    )
    async def learningnewmoves(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "## Learning New Moves\n" + self.data["learningnewmoves"]
        )

    @app_commands.command(
        name="retraining",
        description="Display Training Point costs for retraining"
    )
    async def retraining(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "## Retraining\n" + self.data["retraining"]
        )


async def setup(bot):
    await bot.add_cog(TrainingReferenceCog(bot))
