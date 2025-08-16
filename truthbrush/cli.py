import json
import click
from datetime import date, datetime, timezone
from .api import Api

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.pass_context
def cli(ctx):
    """
    TruthBrush-Modified: A re-engineered API client for Truth Social.
    Requires a .env file in the run directory.
    """
    # This is the corrected initialization. It creates the Api object
    # after the environment is ready and passes it to other commands.
    ctx.obj = Api()

@cli.command()
@click.argument("group_id")
@click.option("--limit", default=20, help="Limit the number of items returned", type=int)
@click.pass_context
def groupposts(ctx, group_id: str, limit: int):
    """Pull posts from a group's timeline."""
    api = ctx.obj
    for post in api.groupposts(group_id, limit=limit):
        print(json.dumps(post))

@cli.command()
@click.pass_context
def trends(ctx):
    """Pull trendy Truths."""
    api = ctx.obj
    trending_posts = api.trending_truths()
    if trending_posts:
        for post in trending_posts:
            print(json.dumps(post))

@cli.command()
@click.pass_context
def tags(ctx):
    """Pull trendy tags."""
    api = ctx.obj
    print(json.dumps(api.tags()))

@cli.command()
@click.pass_context
def grouptags(ctx):
    """Pull group tags."""
    api = ctx.obj
    print(json.dumps(api.group_tags()))

@cli.command()
@click.pass_context
def grouptrends(ctx):
    """Pull group trends."""
    api = ctx.obj
    print(json.dumps(api.trending_groups()))

@cli.command()
@click.pass_context
def groupsuggestions(ctx):
    """Pull group suggestions."""
    api = ctx.obj
    print(json.dumps(api.suggested_groups()))

@cli.command()
@click.argument("handle")
@click.pass_context
def user(ctx, handle: str):
    """Pull a user's metadata."""
    api = ctx.obj
    print(json.dumps(api.lookup(handle)))

@cli.command()
@click.argument("query")
@click.option("--searchtype", type=click.Choice(["statuses", "accounts", "hashtags", "groups"]), default="statuses", help="Type of content to search for.")
@click.option("--limit", default=40, help="Number of results per page.")
@click.option("--created-after", type=click.DateTime(), help="Filter posts on or after this date (YYYY-MM-DD).")
@click.option("--created-before", type=click.DateTime(), help="Filter posts on or before this date (YYYY-MM-DD).")
@click.option("--resolve", type=bool, default=False, help="Resolve URLs in search.")
@click.pass_context
def search(ctx, query: str, searchtype: str, limit: int, created_after: datetime, created_before: datetime, resolve: bool):
    """Search for posts, accounts, or hashtags by a keyword."""
    api = ctx.obj
    if created_after and created_after.tzinfo is None:
        created_after = created_after.replace(tzinfo=timezone.utc)
    if created_before and created_before.tzinfo is None:
        created_before = created_before.replace(tzinfo=timezone.utc)

    for item in api.search(searchtype=searchtype, query=query, limit=limit, created_after=created_after, created_before=created_before, resolve=resolve):
        print(json.dumps(item))

@cli.command()
@click.pass_context
def suggestions(ctx):
    """Pull the list of suggested users."""
    api = ctx.obj
    suggested_users = api.suggestions()
    if suggested_users:
        for user in suggested_users:
            print(json.dumps(user))

@cli.command()
@click.pass_context
def ads(ctx):
    """Pull ads."""
    api = ctx.obj
    print(json.dumps(api.ads()))

@cli.command()
@click.argument("username")
@click.option("--replies/--no-replies", default=False, help="Include replies.")
@click.option("--created-after", type=click.DateTime(), help="Scrape posts on or after this date (YYYY-MM-DD).")
@click.option("--created-before", type=click.DateTime(), help="Scrape posts on or before this date (YYYY-MM-DD).")
@click.option("--pinned/--all", default=False, help="Only pull pinned posts.")
@click.pass_context
def statuses(ctx, username: str, replies: bool, created_after: datetime, created_before: datetime, pinned: bool):
    """Pull a user's posts (statuses)."""
    api = ctx.obj
    if created_after and created_after.tzinfo is None:
        created_after = created_after.replace(tzinfo=timezone.utc)
    if created_before and created_before.tzinfo is None:
        created_before = created_before.replace(tzinfo=timezone.utc)

    for post in api.pull_statuses(username, replies=replies, created_after=created_after, created_before=created_before, pinned=pinned):
        print(json.dumps(post))

@cli.command()
@click.argument("post_id")
@click.option("--limit", default=40, help="Number of likers per page.")
@click.pass_context
def likes(ctx, post_id: str, limit: int):
    """Pull the list of users who liked a post."""
    api = ctx.obj
    for liker in api.user_likes(post_id, limit=limit):
        print(json.dumps(liker))

@cli.command()
@click.argument("post_id")
@click.option("--limit", default=50, help="The maximum number of comments to fetch.")
@click.option(
    "--sort-by",
    help="Sort comments by engagement or time.",
    type=click.Choice(["trending", "controversial", "newest", "oldest"]),
    default="trending",
)
@click.pass_context
def comments(ctx, post_id: str, limit: int, sort_by: str):
    """Pull the top comments for a specific post ID."""
    api = ctx.obj
    for comment in api.pull_comments(post_id=post_id, top_num=limit, sort_by=sort_by):
        print(json.dumps(comment))