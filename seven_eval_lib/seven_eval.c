// Cole este conteúdo completo no seu arquivo seven_eval_lib/seven_eval.c

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "poker.h" // Inclui o protótipo da nossa função de avaliação

// --- A LÓGICA DE AVALIAÇÃO RÁPIDA (A MESMA DE ANTES) ---
// Esta parte não muda, é o nosso motor.
static int find_hand_c(int *cards, int n_cards) {
    int i, best = 9999, rank, suit, suit_counts[] = {0,0,0,0}, is_flush = 0;
    long long hand_binary = 0, suit_binary = 0, flush_binary = 0;
    
    for (i = 0; i < n_cards; i++) {
        rank = cards[i] >> 8;
        suit = cards[i] & 0xF;
        suit_counts[suit]++;
        hand_binary |= (long long)1 << (rank-2);
        suit_binary |= (long long)1 << (16*suit + rank-2);
    }
    
    for (i = 0; i < 4; i++) {
        if (suit_counts[i] >= 5) {
            is_flush = 1;
            flush_binary = (suit_binary >> (16*i)) & 0x3FFF;
            break;
        }
    }

    int hand_values[7];
    for (i = 0; i < n_cards; i++)
        hand_values[i] = (cards[i] >> 8) - 2;

    int quads, trips, pairs;
    int counts[13];
    for(i = 0; i < 13; i++) counts[i] = 0;
    for(i = 0; i < n_cards; i++) counts[hand_values[i]]++;

    quads = trips = pairs = 0;
    for(i = 12; i >= 0; i--) {
        if(counts[i] == 4) quads++;
        else if(counts[i] == 3) trips++;
        else if(counts[i] == 2) pairs++;
    }

    if (is_flush) {
        if (flush_binary & (flush_binary >> 1) & (flush_binary >> 2) & (flush_binary >> 3) & (flush_binary >> 4)) return 1; // Straight Flush
        if (flush_binary == 0x100F) return 1; // Ace-low straight flush
        return 4; // Flush
    }

    if (quads > 0) return 2; // Four of a Kind
    if (trips > 0 && pairs > 0) return 3; // Full House
    if (trips > 1) return 3; // Full House

    if (hand_binary & (hand_binary >> 1) & (hand_binary >> 2) & (hand_binary >> 3) & (hand_binary >> 4)) return 5; // Straight
    if (hand_binary == 0x100F) return 5; // Ace-low straight
    
    if (trips > 0) return 6; // Three of a Kind
    if (pairs > 1) return 7; // Two Pair
    if (pairs > 0) return 8; // One Pair
    
    return 9; // High Card
}


// --- A "PONTE" ENTRE PYTHON E C ---
// Esta é a função que o Python irá chamar.
static PyObject* seven_eval_find_hand(PyObject* self, PyObject* args) {
    PyObject *list;
    int i, n_cards;
    
    // Converte os argumentos do Python (uma lista) para um objeto que o C entende
    if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &list)) {
        PyErr_SetString(PyExc_TypeError, "Parameter must be a list.");
        return NULL;
    }

    n_cards = PyList_Size(list);
    if (n_cards < 5 || n_cards > 7) {
        PyErr_SetString(PyExc_ValueError, "List must contain 5 to 7 integers.");
        return NULL;
    }

    int c_cards[7];
    for (i = 0; i < n_cards; i++) {
        PyObject *item = PyList_GetItem(list, i);
        if (!PyLong_Check(item)) {
            PyErr_SetString(PyExc_TypeError, "List items must be integers.");
            return NULL;
        }
        c_cards[i] = PyLong_AsLong(item);
    }

    // Chama a nossa função C rápida
    int result = find_hand_c(c_cards, n_cards);

    // Converte o resultado de volta para um objeto Python e o retorna
    return PyLong_FromLong(result);
}

// --- DEFINIÇÃO DO MÓDULO PARA O PYTHON ---
// Lista dos métodos que nosso módulo terá (no caso, apenas um)
static PyMethodDef SevenEvalMethods[] = {
    {"find_hand", seven_eval_find_hand, METH_VARARGS, "Evaluates a 5 to 7 card poker hand."},
    {NULL, NULL, 0, NULL} // Marcador de fim da lista
};

// Estrutura de definição do módulo
static struct PyModuleDef seven_eval_module = {
    PyModuleDef_HEAD_INIT,
    "seven_eval", // Nome do módulo
    "A fast 7-card poker hand evaluator.", // Descrição
    -1,
    SevenEvalMethods
};

// --- A FUNÇÃO DE INICIALIZAÇÃO QUE ESTAVA FALTANDO ---
// Esta é a função que o Python procura quando você faz 'import seven_eval'
PyMODINIT_FUNC PyInit_seven_eval(void) {
    return PyModule_Create(&seven_eval_module);
}