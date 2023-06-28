#ifndef GAMEAWESOME_BOARD_HPP
#define GAMEAWESOME_BOARD_HPP

#include <cstdint>
#include <array>
#include <utility>

class Board {
    // TODO: a board that's as general as possible
};

template<typename Field, std::size_t _width, std::size_t _height>
class CheckerBoard: public Board {
public:
    constexpr static std::size_t width = _width, height = _height;
    std::array<std::array<Field, width>, height> board;

    std::array<Field, width>& operator[] (std::size_t index) { return board[index]; }
    const std::array<Field, width>& operator[] (std::size_t index) const { return board[index]; }
    Field& operator[] (std::pair<std::size_t, std::size_t> index) { return board[index.first][index.second]; }
    const Field& operator[] (std::pair<std::size_t, std::size_t> index) const { return board[index.first][index.second]; }

    constexpr static std::size_t getSize() { return width * height; }
    constexpr static std::pair<std::size_t, std::size_t> getDimensions() { return std::make_pair(width, height); };
};

#endif //GAMEAWESOME_BOARD_HPP
