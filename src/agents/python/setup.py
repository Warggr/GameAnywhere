from distutils.core import setup, Extension

def main():
	setup(name="pyerre",
		version="1.0.0",
		description="aien aristeuein kai hypeirochon emmenai allôn",
		author="Pierre Ballif",
		author_email="pierre.ballif@tum.de",
		ext_modules=[Extension("pyerre", ["main.cpp"])]
	)

if __name__=="__main__":
	main()
