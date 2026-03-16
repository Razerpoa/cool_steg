import typer
import zlib
import magic
import mimetypes
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
from .qr import generate_qr_pixels, decode_qr_from_pixels
from .rle import encode_rle, decode_rle, step_2_compression, step_2_decompression
from .stegano import embed_data, extract_data, get_img_from_path

app = typer.Typer(
    name="qr-changer",
    help="A cool CLI tool to hide and reveal QR code messages in images.",
    rich_markup_mode="rich"
)
console = Console()

@app.command()
def hide(
    message: str = typer.Option(None, "--message", "-m", help="The message to hide."),
    file: Path = typer.Option(None, "--file", "-f", help="Path to a file to hide.", exists=True, file_okay=True, dir_okay=False),
    cover: Path = typer.Option(None, "--image", "-i", help="Path to the cover image.", exists=True, file_okay=True, dir_okay=False),
    seed: int = typer.Option(4589, "--seed", "-s", help="Seed for random pixel selection."),
    rle: bool = typer.Option(False, "--rle", help="Print only RLE result."),
    file_out: Path = typer.Option(None, "--file-out", "-fo", help="Output of the result"),
    no_qr: bool = typer.Option(False, "--no-qr", "-nq", help="Don't use QR Code"),
):
    """
    [bold green]Hide[/bold green] a message inside an image as a QR code.
    """
    data_from_user = "".encode()
    if file:
        no_qr = True
        try:
            data_from_user = Path(file).read_bytes()
        except Exception as e:
            console.print(Panel.fit(
                f"[bold red]Error:[/bold red] Failed to read file: {e}",
                title="Cool Steg - Hide"
            ))
            raise typer.Exit(code=1)
        data_from_user = zlib.compress(data_from_user)

    if message:
        data_from_user = message.encode()
            
    # if message is None or file is None:
    #     console.print(Panel.fit(
    #         f"[bold red]Error:[/bold red] Either message or file must be provided.",
    #         title="Cool Steg - Hide"
    #     ))
    #     raise typer.Exit(code=1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        output = cover if not file_out else file_out
        if not rle and cover is None:
            console.print(Panel.fit(
                f"[bold red]Error:[/bold red] Cover image is required.",
                title="Cool Steg - Hide"
            ))
            raise typer.Exit(code=1)
        
        task = progress.add_task("Processing...", total=5)

        if not no_qr:
            progress.update(task, description="Generating QR code...")
            pixels, size = generate_qr_pixels(data_from_user)

            progress.update(task, advance=1, description="Compressing pixels (Step 1 RLE)...")
            data_from_user = encode_rle(pixels)
            
            progress.update(task, advance=1, description="Appending size to RLE data...")
            if len(str(size[0])) < 3:
                data_from_user += "0"
            data_from_user += str(size[0])

            progress.update(task, advance=1, description="Compressing pixels (Step 2 RLE)...")
            data_from_user = step_2_compression(data_from_user).encode()
        
        if rle:
            progress.stop()
            console.print(
                f"\n[bold green]RLE Encoded![/bold green]\n"
                f"RLE Data:\n[cyan]{data_from_user.decode()}[/cyan]\n"
                f"Length: [yellow]{len(data_from_user)}[/yellow]"
            )
            raise typer.Exit()
        
        progress.update(task, advance=1, description="Embedding data into image...")
        try:
            img = get_img_from_path(str(cover))
            img = embed_data(img, data_from_user, seed)
            img.save(output)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

        progress.update(task, advance=1)

    console.print(Panel.fit(
        f"[bold green]Success![/bold green]\n\n"
        f"Message hidden in [cyan]{output}[/cyan]\n"
        f"Using seed: [yellow]{seed}[/yellow]",
        title="Cool Steg - Hide"
    ))

@app.command()
def reveal(
    image: Path = typer.Option(None, "--image", "-i", help="Path to the stegano image.", exists=True, file_okay=True, dir_okay=False),
    file: Path = typer.Option("out", "--file-out", "-fo", help="Path to the output file (without extension) if data is considered a file", dir_okay=False, file_okay=True),
    seed: int = typer.Option(4589, "--seed", "-s", help="Seed used during hiding."),
    rle: str = typer.Option(None, "--rle", help="Provide RLE data directly instead of from an image."),
    show_rle: bool = typer.Option(False, "--show-rle", help="Show decompressed RLE string and exit."),
    no_qr: bool = typer.Option(False, "--no-qr", "-nq", help="Don't decode to qr"),
):
    """
    [bold magenta]Reveal[/bold magenta] a hidden message from an image.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        goes_smooth = True
        to_a_file = False
        # is_string = False

        # TODO: don't do this
        extracted_data = ""
        rle_string = ""
        filepath = ""

        task = progress.add_task("Processing...", total=4)

        if rle:
            # Use provided RLE data
            extracted_data = rle
            progress.update(task, advance=1)
        elif image:
            # 1. Extract RLE data from stegano image
            progress.update(task, description="Extracting data from image...")
            try:
                img = get_img_from_path(str(image))
                extracted_data = extract_data(img, seed)
                extracted_data = extracted_data.decode()
                
            except UnicodeDecodeError as e:
                console.print(f"[bold blue]Info:[/bold blue] Data seems to be in bytes or string. Decoding without QR Code ")
                no_qr = True

                # extracted_data = extracted_data.decode(errors="replace")
                # goes_smooth = False
                # raise typer.Exit(code=1)
            
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] Failed to extract data. Check your seed. ({e})")
                raise typer.Exit(code=1)
            progress.update(task, advance=1)
            progress.stop()
        else:
            console.print(Panel.fit(
                f"[bold red]Error:[/bold red] Either image or RLE data must be provided.",
                title="Cool Steg - Reveal"
            ))
            raise typer.Exit(code=1)
        
        # 2. Decompress Step 2 then Step 1
        progress.update(task, description="Decompressing pixels (Step 2 RLE)...")
        if isinstance(extracted_data, str):
            try:
                rle_string = step_2_decompression(extracted_data)
            except Exception as e:
                console.print("[bold red]Error:[/bold red] Failed to decompress Show anyway...")
                goes_smooth = False

        if isinstance(extracted_data, bytes):
            try: extracted_data = zlib.decompress(extracted_data)
            except Exception as e: pass
            try: extracted_data = extracted_data.decode()
            except UnicodeDecodeError as e: console.print("[bold blue]Info:[/bold blue] File is not str")

            if len(extracted_data) > 100:
                console.print("[bold blue]Info:[/bold blue] Data is longer than 100 chars")
                to_a_file = True

        if not no_qr:
            try:
                qr_size = int(rle_string[-3:])
                qr_size = (qr_size,  qr_size)
                rle_string = rle_string[:-3]

                progress.update(task, advance=1, description="Decompressing pixels (Step 1 RLE)...")
                pixels = decode_rle(rle_string)
            
                progress.update(task, advance=1, description="Decoding QR Code...")
                extracted_data = decode_qr_from_pixels(pixels, qr_size)
            except ValueError as e:
                pass
            except Exception as e:
                console.print("[bold red]Error:[/bold red] Failed to decode QR")
                goes_smooth = False
                

        if show_rle:
            console.print(
                f"[bold green]RLE Decoded![/bold green]\n"
                f"RLE Data:\n[cyan]{rle_string}[/cyan]\n"
                f"Length: [yellow]{len(rle_string)}[/yellow]"
            )
            raise typer.Exit()
        if to_a_file:
            filepath = str(file)
            if isinstance(extracted_data, str):
                filepath += ".txt"
                console.print(f"[bold blue]Info:[/bold blue] Saving to {filepath}...")
                open(filepath, "w").write(extracted_data)
            else:
                m = magic.Magic(mime=True)
                mime = m.from_buffer(extracted_data)
                extension = mimetypes.guess_extension(mime)
                if mime and extension:
                    console.print(f"[bold blue]Info:[/bold blue] File mime seems to be [white]{mime}[/white]")
                    filepath += extension
                console.print(f"[bold blue]Info:[/bold blue] Saving to {filepath}...")
                open(filepath, "wb").write(extracted_data)

        # 3. Save as QR code image
        # progress.add_task(description="Saving revealed QR code...", total=None)
        # save_qr_from_pixels(pixels, qr_size, str(output_qr))

        progress.update(task, advance=1)

    if goes_smooth:
        if to_a_file:
            console.print(Panel.fit(
                f"[bold green]Decoded Successfully![/bold green]\n\n"
                f"Using seed: [yellow]{seed}[/yellow]\n"
                f"\nFile output: [white]{filepath}[/white]",
                title="Cool Steg - Reveal"
            ))
        else:
            console.print(Panel.fit(
                f"[bold green]Decoded Successfully![/bold green]\n\n"
                f"Using seed: [yellow]{seed}[/yellow]\n"
                f"\nDecoded Message: [white]{extracted_data}[/white]",
                title="Cool Steg - Reveal"
            ))
    else:
        console.print(Panel.fit(
            f"[bold yellow]Decoding didn't goes smoothly[/bold yellow]\n\n"
            f"Using seed: [yellow]{seed}[/yellow]\n"
            f"Extracted Data: [white]{extracted_data[:100]}[/white]",
            title="Cool Steg - Reveal"
        ))

def main():
    app()

if __name__ == "__main__":
    main()
