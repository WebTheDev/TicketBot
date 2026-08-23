"""The /config command group: live configuration management from inside Discord.

Every mutating command writes to PostgreSQL and then refreshes the runtime cache before
replying, so the confirmation always reflects what is actually live.
"""

import discord
from discord import app_commands

from ticketbot.bot import bot, ticket
from ticketbot.utils.config_validation import (
    SETTING_GROUPS,
    SETTING_SPECS,
    SPECS_BY_KEY,
    ConfigValidationError,
    coerce_setting,
    describe_removal_block,
    format_setting_value,
    parse_message_id,
    validate_room_for_new_type,
    validate_type_fields,
)
from ticketbot.utils.database import ConfigRepository, TicketRepository
from ticketbot.utils.helpers import apply_presence, build_creation_embed
from ticketbot.utils.runtime_config import settings

PRESENCE_KEYS = {"bot_status_type", "bot_status_message"}
APPEARANCE_KEYS = {"embed_color", "footer_of_embeds"}

MAX_FIELD_LENGTH = 1024


def is_config_manager(user: discord.abc.User) -> bool:
    """Bot owner, or a guild administrator."""
    if user.id == settings.debug_log_send_id:
        return True
    guild_permissions = getattr(user, "guild_permissions", None)
    return bool(guild_permissions and guild_permissions.administrator)


def underline(text: str) -> str:
    return f"__{text}__"


def config_embed(title: str, description: str, user: discord.abc.User) -> discord.Embed:
    embed = discord.Embed(
        title=underline(title), description=description, color=settings.embed_color
    )
    embed.set_author(name=f"{user}", icon_url=user.display_avatar)
    embed.set_footer(
        text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f"{bot.user.display_avatar}"
    )
    return embed


def add_section(embed: discord.Embed, name: str, value: str) -> None:
    embed.add_field(name=underline(name), value=clamp_field(value), inline=False)


def clamp_field(text: str) -> str:
    if len(text) <= MAX_FIELD_LENGTH:
        return text
    notice = "\n… (truncated)"
    return text[: MAX_FIELD_LENGTH - len(notice)].rstrip() + notice


def format_roles(role_ids: tuple[int, ...]) -> str:
    return ", ".join(f"<@&{role_id}>" for role_id in role_ids) if role_ids else "*No roles yet*"


def format_type_name(ticket_type) -> str:
    return f"**{ticket_type.label}** `{ticket_type.key}`"


def no_types_yet() -> str:
    return "*I don't have any ticket types yet.* Add one with `/ticket config types add`."


def unknown_type_embed(type_key: str, user: discord.abc.User) -> discord.Embed:
    known = settings.ticket_types
    known_text = (
        "\n".join(f"• {format_type_name(ticket_type)}" for ticket_type in known)
        if known
        else no_types_yet()
    )
    embed = config_embed(
        "Unknown Ticket Type", f"I don't have a ticket type with the key `{type_key}`.", user
    )
    add_section(embed, "Types I Do Have", known_text)
    return embed


async def deny(interaction: discord.Interaction) -> None:
    embed = config_embed(
        "Permission Denied",
        "Only my owner or a server administrator can manage my configuration. ❌",
        interaction.user,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def refresh_creation_embed() -> bool:
    """Re-render the persistent "Create a ticket" message, returning whether it was found."""
    from ticketbot.functions.create import TicketCreation

    message_id = settings.creation_message_id
    if not message_id:
        return False
    channel = bot.get_channel(settings.id_of_channel_to_send_ticket_creation_embed)
    if channel is None:
        return False
    try:
        message = await channel.fetch_message(message_id)
    except (discord.HTTPException, discord.NotFound):
        return False
    embed = build_creation_embed(bot, settings.embed_color, settings.footer_of_embeds)
    await message.edit(embed=embed, view=TicketCreation(timeout=None))
    return True


async def type_key_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Autocomplete ticket type keys from the cache."""
    current = current.lower()
    return [
        app_commands.Choice(name=f"{ticket_type.label} ({ticket_type.key})", value=ticket_type.key)
        for ticket_type in settings.ticket_types
        if current in ticket_type.key.lower() or current in ticket_type.label.lower()
    ][:25]


@app_commands.default_permissions(administrator=True)
class ConfigGroup(app_commands.Group):
    """Manage my live configuration."""


config_group = ConfigGroup(name="config", description="Manage my live configuration")
types_group = app_commands.Group(
    name="types", description="Manage my ticket types", parent=config_group
)
roles_group = app_commands.Group(
    name="roles",
    description="Manage which roles staff each of my ticket types",
    parent=config_group,
)


@config_group.command(name="show", description="Show you my current live configuration")
async def show(interaction: discord.Interaction):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    embed = config_embed(
        "My Configuration",
        "These settings are live — when you change one I apply it immediately, no restart needed.",
        interaction.user,
    )

    ticket_types = settings.ticket_types
    if ticket_types:
        types_text = "\n".join(
            f"{format_type_name(ticket_type)}\n ↳ {format_roles(settings.roles_for(ticket_type.key))}"
            for ticket_type in ticket_types
        )
    else:
        types_text = no_types_yet()
    add_section(embed, f"🎫 Ticket Types ({len(ticket_types)})", types_text)

    for group in SETTING_GROUPS:
        lines = [
            f"**{spec.label}** — `{format_setting_value(spec.key, getattr(settings, spec.key))}`"
            for spec in SETTING_SPECS
            if spec.group == group
        ]
        add_section(embed, group, "\n".join(lines))

    creation_message_id = settings.creation_message_id
    add_section(
        embed,
        "Managed Automatically",
        f"**Ticket Creation Message** — `{creation_message_id}`"
        if creation_message_id
        else "**Ticket Creation Message** — *I haven't posted it yet*",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@config_group.command(name="set", description="Change one of my live settings")
@app_commands.describe(
    setting="The setting you want me to change",
    value="The new value I should use (e.g. #5865F2 for Embed Color, or true/false for a toggle)",
)
@app_commands.choices(
    setting=[app_commands.Choice(name=spec.label, value=spec.key) for spec in SETTING_SPECS]
)
async def set_setting(
    interaction: discord.Interaction, setting: app_commands.Choice[str], value: str
):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    spec = SPECS_BY_KEY[setting.value]
    previous = format_setting_value(spec.key, getattr(settings, spec.key))

    try:
        coerced = coerce_setting(spec.key, value)
    except ConfigValidationError as error:
        embed = config_embed(
            f"I Couldn't Set {spec.label}", f"{error}\n\n{spec.help}", interaction.user
        )
        add_section(embed, "Example", f"`{spec.example}`")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    await settings.set_value(spec.key, coerced)

    notes = []
    if spec.key in PRESENCE_KEYS:
        recognized = await apply_presence(
            bot, settings.bot_status_type, settings.bot_status_message
        )
        notes.append(
            "I updated my presence."
            if recognized
            else "I updated my presence, but that status type is unrecognized so I used "
            "**Playing**."
        )
    if spec.key in APPEARANCE_KEYS:
        notes.append(
            "I refreshed the ticket creation message."
            if await refresh_creation_embed()
            else "I couldn't refresh the ticket creation message — I wasn't able to find it."
        )

    embed = config_embed(
        f"{spec.label} Updated",
        f"{spec.help}\n\n**Before** — `{previous}`\n"
        f"**Now** — `{format_setting_value(spec.key, coerced)}`",
        interaction.user,
    )
    if notes:
        add_section(embed, "I Also Applied", "\n".join(f"• {note}" for note in notes))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@config_group.command(
    name="creation-message",
    description="Use a message I already posted as my ticket creation embed",
)
@app_commands.describe(
    message="The message ID or link I should adopt as my ticket creation embed",
)
async def creation_message(interaction: discord.Interaction, message: str):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    try:
        message_id = parse_message_id(message)
    except ConfigValidationError as error:
        return await interaction.response.send_message(
            embed=config_embed("That Isn't A Message ID", str(error), interaction.user),
            ephemeral=True,
        )

    channel = bot.get_channel(settings.id_of_channel_to_send_ticket_creation_embed)
    if channel is None:
        return await interaction.response.send_message(
            embed=config_embed(
                "I Can't Reach That Channel",
                f"I can't see the channel I'm configured to post the creation embed in "
                f"(`{settings.id_of_channel_to_send_ticket_creation_embed}`). Check "
                "`ID_OF_CHANNEL_TO_SEND_TICKET_CREATION_EMBED` in `.env` and my permissions.",
                interaction.user,
            ),
            ephemeral=True,
        )

    try:
        target = await channel.fetch_message(message_id)
    except discord.NotFound:
        return await interaction.response.send_message(
            embed=config_embed(
                "I Couldn't Find That Message",
                f"There's no message `{message_id}` in {channel.mention}. I relink my creation "
                "embed from that channel on every startup, so the message has to live there.",
                interaction.user,
            ),
            ephemeral=True,
        )
    except discord.HTTPException as error:
        return await interaction.response.send_message(
            embed=config_embed(
                "I Couldn't Fetch That Message",
                f"Discord wouldn't let me read `{message_id}` in {channel.mention}: {error}",
                interaction.user,
            ),
            ephemeral=True,
        )

    if target.author.id != bot.user.id:
        return await interaction.response.send_message(
            embed=config_embed(
                "I Can't Edit That Message",
                f"{target.author.mention} sent that message, and Discord only lets me edit my "
                "own. Point me at a message I posted, or let me create a fresh one.",
                interaction.user,
            ),
            ephemeral=True,
        )

    previous_id = settings.creation_message_id
    await settings.set_value("creation_message_id", message_id)
    relinked = await refresh_creation_embed()

    detached = False
    if previous_id and previous_id != message_id:
        detached = await detach_creation_message(channel, previous_id)

    embed = config_embed(
        "Ticket Creation Embed Updated",
        f"I've adopted [that message]({target.jump_url}) as my ticket creation embed and saved "
        "it to my configuration. I'll relink to it on every restart."
        + (
            " Its button works now."
            if relinked
            else "\n\n⚠️ I saved the ID but couldn't rewrite the message itself, so its button "
            "may not work until my next restart."
        ),
        interaction.user,
    )
    add_section(embed, "Message", f"**ID** — `{message_id}`\n**Channel** — {channel.mention}")
    if previous_id and previous_id != message_id:
        add_section(
            embed,
            "Previous Embed",
            f"`{previous_id}` "
            + (
                "— I removed its button so there aren't two live ones."
                if detached
                else "— I couldn't remove its button; delete that message if it still has one."
            ),
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def detach_creation_message(channel: discord.abc.Messageable, message_id: int) -> bool:
    """Strip the button off a superseded creation message, returning whether it worked."""
    try:
        stale = await channel.fetch_message(message_id)
        await stale.edit(view=None)
    except (discord.HTTPException, discord.NotFound):
        return False
    return True


@types_group.command(name="list", description="List the ticket types I have configured")
async def types_list(interaction: discord.Interaction):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    ticket_types = settings.ticket_types
    if not ticket_types:
        embed = config_embed("Ticket Types", no_types_yet(), interaction.user)
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    embed = config_embed(
        "Ticket Types",
        "Active Ticket Types available to server Members.",
        interaction.user,
    )
    for index, ticket_type in enumerate(ticket_types, start=1):
        add_section(
            embed,
            f"{index}. {ticket_type.label}",
            f"{ticket_type.description}\n"
            f"**Key** — `{ticket_type.key}`\n"
            f"**Staff Roles** — {format_roles(settings.roles_for(ticket_type.key))}",
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@types_group.command(name="add", description="Add a ticket type to my creation dropdown")
@app_commands.describe(
    key="Short internal name I use in commands and role permissions (e.g. sales)",
    label="The name I show members in the dropdown (e.g. Sales 💲)",
    description="The one-line explanation I show under the label",
    position="Where I place it in the dropdown; lower numbers come first",
)
async def types_add(
    interaction: discord.Interaction,
    key: str,
    label: str,
    description: str,
    position: int | None = None,
):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    try:
        validate_type_fields(key, label, description)
        validate_room_for_new_type(settings.known_type_keys(), key)
    except ConfigValidationError as error:
        return await interaction.response.send_message(
            embed=config_embed("I Couldn't Add That Ticket Type", str(error), interaction.user),
            ephemeral=True,
        )

    if position is None:
        position = len(settings.ticket_types)
    await ConfigRepository.upsert_type(key, label, description, position)
    await settings.refresh()

    embed = config_embed(
        "Ticket Type Added",
        f"**{label}** is live — I show it the next time someone opens the ticket dropdown.",
        interaction.user,
    )
    add_section(
        embed,
        "Details",
        f"{description}\n**Key** — `{key}`\n**Dropdown Position** — `{position}`",
    )
    add_section(
        embed,
        "Next Step",
        "I can't let any staff roles see these tickets yet. Add one with\n"
        f"`/ticket config roles add type:{key}`",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@types_group.command(name="edit", description="Change one of my existing ticket types")
@app_commands.describe(
    type="The ticket type you want me to edit",
    label="The new name I show members in the dropdown; leave blank to keep it",
    description="The new one-line explanation I show; leave blank to keep it",
    position="The new dropdown position I should use; leave blank to keep it",
)
@app_commands.autocomplete(type=type_key_autocomplete)
async def types_edit(
    interaction: discord.Interaction,
    type: str,
    label: str | None = None,
    description: str | None = None,
    position: int | None = None,
):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    existing = await ConfigRepository.find_type(type)
    if existing is None:
        return await interaction.response.send_message(
            embed=unknown_type_embed(type, interaction.user), ephemeral=True
        )

    new_label = label if label is not None else existing.label
    new_description = description if description is not None else existing.description
    new_position = position if position is not None else existing.position

    try:
        validate_type_fields(type, new_label, new_description)
    except ConfigValidationError as error:
        return await interaction.response.send_message(
            embed=config_embed("I Couldn't Edit That Ticket Type", str(error), interaction.user),
            ephemeral=True,
        )

    await ConfigRepository.upsert_type(type, new_label, new_description, new_position)
    await settings.refresh()

    embed = config_embed(
        "Ticket Type Updated",
        f"**{new_label}** is live — I show the change the next time someone opens the dropdown.",
        interaction.user,
    )
    add_section(
        embed,
        "Details",
        f"{new_description}\n**Key** — `{type}`\n**Dropdown Position** — `{new_position}`",
    )
    add_section(embed, "Staff Roles", format_roles(settings.roles_for(type)))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@types_group.command(name="remove", description="Remove one of my ticket types")
@app_commands.describe(
    type="The ticket type you want me to remove",
    force="Remove it even if I still have open tickets of this type",
)
@app_commands.autocomplete(type=type_key_autocomplete)
async def types_remove(interaction: discord.Interaction, type: str, force: bool = False):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    label = next((t.label for t in settings.ticket_types if t.key == type), None)
    if label is None:
        return await interaction.response.send_message(
            embed=unknown_type_embed(type, interaction.user), ephemeral=True
        )

    open_tickets = await TicketRepository.count_by_type(type)
    if open_tickets and not force:
        return await interaction.response.send_message(
            embed=config_embed(
                "That Ticket Type Is Still In Use",
                describe_removal_block(type, open_tickets),
                interaction.user,
            ),
            ephemeral=True,
        )

    await ConfigRepository.delete_type(type)
    await settings.refresh()

    embed = config_embed(
        "Ticket Type Removed",
        f"I've dropped **{label}** (`{type}`) and its staff role permissions. Members can no "
        "longer pick it from my ticket dropdown.",
        interaction.user,
    )
    if open_tickets:
        add_section(
            embed,
            "⚠️ Heads Up",
            f"I still have {open_tickets} open ticket(s) of this type. They keep working, but "
            "staff role permissions no longer apply to them.",
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@roles_group.command(name="list", description="Show you which roles staff each of my ticket types")
async def roles_list(interaction: discord.Interaction):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    ticket_types = settings.ticket_types
    if not ticket_types:
        embed = config_embed("Staff Roles", no_types_yet(), interaction.user)
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    embed = config_embed(
        "Staff Roles",
        "I let members with these roles see and manage tickets of each type.",
        interaction.user,
    )
    for ticket_type in ticket_types:
        add_section(
            embed,
            ticket_type.label,
            f"`{ticket_type.key}` → {format_roles(settings.roles_for(ticket_type.key))}",
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@roles_group.command(name="add", description="Let a role staff one of my ticket types")
@app_commands.describe(
    type="The ticket type I should let the role staff",
    role="The role I should grant access to",
)
@app_commands.autocomplete(type=type_key_autocomplete)
async def roles_add(interaction: discord.Interaction, type: str, role: discord.Role):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    label = next((t.label for t in settings.ticket_types if t.key == type), None)
    if label is None:
        return await interaction.response.send_message(
            embed=unknown_type_embed(type, interaction.user), ephemeral=True
        )

    await ConfigRepository.add_role(type, role.id)
    await settings.refresh()

    embed = config_embed(
        "Staff Role Added",
        f"{role.mention} can now staff **{label}** tickets. I apply this to tickets created "
        "from now on — it does not change channels that already exist.",
        interaction.user,
    )
    add_section(embed, f"All {label} Staff Roles", format_roles(settings.roles_for(type)))
    await interaction.response.send_message(embed=embed, ephemeral=True)


@roles_group.command(name="remove", description="Stop a role from staffing one of my ticket types")
@app_commands.describe(
    type="The ticket type I should remove the role from",
    role="The role I should remove",
)
@app_commands.autocomplete(type=type_key_autocomplete)
async def roles_remove(interaction: discord.Interaction, type: str, role: discord.Role):
    if not is_config_manager(interaction.user):
        return await deny(interaction)

    label = next((t.label for t in settings.ticket_types if t.key == type), type)
    removed = await ConfigRepository.remove_role(type, role.id)
    await settings.refresh()

    if not removed:
        return await interaction.response.send_message(
            embed=config_embed(
                "Nothing To Remove",
                f"{role.mention} wasn't staffing **{label}** tickets, so I didn't change anything.",
                interaction.user,
            ),
            ephemeral=True,
        )

    embed = config_embed(
        "Staff Role Removed",
        f"{role.mention} no longer staffs **{label}** tickets. I apply this to tickets created "
        "from now on — it does not change channels that already exist.",
        interaction.user,
    )
    add_section(embed, f"Remaining {label} Staff Roles", format_roles(settings.roles_for(type)))
    await interaction.response.send_message(embed=embed, ephemeral=True)


ticket.add_command(config_group)
