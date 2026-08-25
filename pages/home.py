import dash
import dash_mantine_components as dmc


dash.register_page(__name__, path='/')


WIP_TEXT = dmc.Text(
	"This is the Home page. Work in progress.",
	fz="xl",
	lh="md",
)


layout = dmc.Box(
    [
        dmc.Carousel(
        [
            dmc.CarouselSlide(dmc.Center(WIP_TEXT, bg="blue", c="white", p=60)),
            dmc.CarouselSlide(dmc.Center(WIP_TEXT, bg="blue", c="white", p=60)),
        ],
        id="carousel-autoscroll",
        emblaOptions={"loop": True},
        autoScroll=True,
    )
], style={"padding": "40px"})
